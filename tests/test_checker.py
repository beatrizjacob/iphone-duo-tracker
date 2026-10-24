import json
import subprocess
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
import checker as c

FIXTURE = Path(__file__).parent / 'fixtures/mediamarkt.json'
PRODUCTS = [{'id': '1674375', 'capacity_gb': 256}, {'id': '1674377', 'capacity_gb': 512}]

class ParsingTests(unittest.TestCase):
    def setUp(self): self.data = json.loads(FIXTURE.read_text())
    def observe(self):
        with patch('checker.time.time', return_value=1792843200):
            return c.mm_observations(self.data, PRODUCTS)
    def test_real_snapshot(self):
        result = self.observe()
        self.assertEqual([x['status'] for x in result], ['unavailable','unknown','unavailable','unknown'])
        self.assertNotIn('earliest', result[0])
        self.assertNotIn('latest', result[0])
    def test_html_extraction(self):
        self.assertEqual(c.extract_mm('<script>window.state={"apolloState":'+json.dumps(self.data)+'};</script>'),self.data)
    def test_changed_html(self):
        with self.assertRaises(c.StopSource): c.extract_mm('<html>new format</html>')
    def test_wrong_color(self):
        self.data['GraphqlProduct:Media:es-ES:1674375']['title']='iPhone Duo Cielo nocturno 256 GB'
        with self.assertRaises(c.StopSource): self.observe()
    def test_wrong_capacity(self):
        self.data['GraphqlProduct:Media:es-ES:1674375']['title']='iPhone Duo Blanco estrella 512 GB'
        with self.assertRaises(c.StopSource): self.observe()
    def test_unverified_enum_never_means_stock(self):
        self.data['CofrDeliveryFeature:Media:es:1674375']['delivery']['deliveryStatus']='SOMETHING_NEW'
        self.assertEqual(self.observe()[0]['status'],'unknown')
    def test_marketplace_never_alerted(self):
        self.data['CofrDeliveryFeature:Media:es:1674375']['isProductOfTypeMarketplace']=True
        self.assertEqual(self.observe()[0]['status'],'unknown')
    def test_expired_estimate(self):
        with patch('checker.time.time',return_value=2_000_000_000):
            self.assertEqual(c.mm_observations(self.data,PRODUCTS)[0]['status'],'unknown')
    def test_no_store_selected_never_pickup_stock(self):
        self.assertTrue(all(x['status']=='unknown' for x in self.observe() if x['channel']=='pickup'))

class AppleTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads(Path('tests/fixtures/apple-pickup.json').read_text())
        self.source=json.loads(Path('config.json').read_text())['sources']['apple']
    def observe(self):return c.apple_observations(self.data,self.source,'08002')
    def entry(self):return self.data['body']['stores'][0]['partsAvailability']['MK2D4QL/A']
    def test_real_snapshot_four_unavailable_pairs(self):
        items=self.observe()
        pickup=[x for x in items if x['channel']=='pickup']
        self.assertEqual(len(pickup),4)
        self.assertEqual({x['status'] for x in pickup},{'unavailable'})
        self.assertEqual({x['store_id'] for x in pickup},{'R368','R406'})
        self.assertEqual(len({x['key'] for x in pickup}),4)
    def test_only_store_stock_is_returned(self):
        self.assertEqual([x['status'] for x in self.observe() if x['channel']=='shipping'],[])
    def test_synthetic_available_transition(self):
        # Synthetic mutation tests behavior; it is not a live in-stock observation.
        self.entry().update(pickupDisplay='available',pickupSearchQuote='Disponible hoy')
        item=self.observe()[0]
        self.assertEqual(item['status'],'available')
        self.assertTrue(c.should_alert(item,{}))
        self.assertFalse(c.should_alert(item,{'last_alert':c.fingerprint(item)}))
    def test_available_now_store_flag_is_not_product_stock(self):
        self.data['body']['stores'][0]['availableNow']=True
        self.assertEqual(self.observe()[0]['status'],'unavailable')
    def test_missing_store_is_error(self):
        self.data['body']['stores'].pop()
        with self.assertRaises(c.StopSource):self.observe()
    def test_missing_part_is_error(self):
        del self.data['body']['stores'][0]['partsAvailability']['MK2D4QL/A']
        with self.assertRaises(c.StopSource):self.observe()
    def test_wrong_location_is_error(self):
        self.data['body']['location']='28001'
        with self.assertRaises(c.StopSource):self.observe()
    def test_wrong_title_is_error(self):
        self.entry()['messageTypes']['regular']['storePickupProductTitle']='iPhone Duo 512 GB blanco estelar'
        with self.assertRaises(c.StopSource):self.observe()
    def test_unknown_status_is_unknown(self):
        self.entry()['pickupDisplay']='new-unknown-status'
        self.assertEqual(self.observe()[0]['status'],'unknown')
    def test_conflicting_quote_is_unknown(self):
        self.entry()['pickupDisplay']='available'
        self.assertEqual(self.observe()[0]['status'],'unknown')
    def test_ineligible_product_is_unknown(self):
        self.entry().update(pickupDisplay='available',pickupSearchQuote='Disponible hoy',storePickEligible=False)
        self.assertEqual(self.observe()[0]['status'],'unknown')
    def test_error_payload_is_not_out_of_stock(self):
        self.data['head']['status']='500'
        with self.assertRaises(c.StopSource):self.observe()

class AlertTests(unittest.TestCase):
    def setUp(self): self.item={'status':'available','scope':'verified test-only fixture'}
    def test_first_stock_alert(self): self.assertTrue(c.should_alert(self.item,{}))
    def test_dedup(self): self.assertFalse(c.should_alert(self.item,{'last_alert':c.fingerprint(self.item)}))
    def test_unknown_does_not_rearm(self):
        state={'last_alert':c.fingerprint(self.item)}
        c.record_observation({'status':'unknown'},state)
        self.assertFalse(c.should_alert(self.item,state))
    def test_confirmed_loss_rearms(self):
        state={'last_alert':c.fingerprint(self.item)}
        c.record_observation({'status':'unavailable'},state)
        self.assertTrue(c.should_alert(self.item,state))
    def test_delayed_offers_never_alert(self):
        self.item['status']='delayed'
        self.assertFalse(c.should_alert(self.item,{}))
    def test_delivery_metadata_does_not_repeat_stock_alert(self):
        previous={'last_alert':c.fingerprint(self.item)}
        self.item['earliest']='synthetic-new-date'
        self.assertFalse(c.should_alert(self.item,previous))

class AccessTests(unittest.TestCase):
    def test_robots_wildcards_and_allow(self):
        rules='User-agent: *\nDisallow: /es/*\nAllow: /es/brand/\nCrawl-delay: 15\n'
        self.assertEqual(c.robots_rules(rules,'/es/brand/apple'),(True,15))
        self.assertFalse(c.robots_rules(rules,'/es/product/a')[0])
    def test_unrelated_ai_allow_not_impersonated(self):
        rules='User-agent: *\nDisallow: /\nUser-agent: GPTBot\nAllow: /\n'
        self.assertFalse(c.robots_rules(rules,'/es/brand/apple')[0])
    def test_block_pauses(self):
        error=urllib.error.HTTPError('https://www.apple.com',541,'blocked',{},None)
        with patch.object(c.OPENER,'open',side_effect=error):
            with self.assertRaises(c.StopSource) as ctx: c.fetch('https://www.apple.com/es/')
            self.assertTrue(ctx.exception.permanent)
    def test_rate_limit_no_immediate_retry(self):
        error=urllib.error.HTTPError('https://www.apple.com',429,'limited',{'Retry-After':'7200'},None)
        with patch.object(c.OPENER,'open',side_effect=error) as request:
            with self.assertRaises(c.StopSource) as ctx: c.fetch('https://www.apple.com/es/')
            self.assertEqual(ctx.exception.delay,7200)
            self.assertEqual(request.call_count,1)
    def test_allowlist(self):
        with self.assertRaises(c.StopSource):c.fetch('https://attacker.example/')
    def test_token_redacted(self):
        with patch('urllib.request.urlopen',side_effect=RuntimeError('secret-token')):
            with self.assertRaises(RuntimeError) as ctx: c.telegram('sendMessage',{},'secret-token')
            self.assertNotIn('secret-token',str(ctx.exception))

class StateIntegrationTests(unittest.TestCase):
    def test_state_branch_roundtrip_preserves_source(self):
        helper = str(Path('state_git.py').resolve())
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); repo=root/'repo'; remote=root/'remote.git'
            subprocess.run(['git','init','--bare',str(remote)],check=True,capture_output=True)
            repo.mkdir()
            def git(*args):
                return subprocess.run(['git',*args],cwd=repo,check=True,capture_output=True,text=True)
            git('init');git('config','user.name','Test');git('config','user.email','test@example.com')
            (repo/'source.txt').write_text('preserve me')
            git('add','source.txt');git('commit','-m','initial');git('remote','add','origin',str(remote))
            def run(mode):subprocess.run(['python3',helper,mode],cwd=repo,check=True,capture_output=True)
            run('load')
            state={'version':1,'sources':{},'items':{'test':{'last_alert':'saved'}}}
            (repo/'state.json').write_text(json.dumps(state));run('save')
            (repo/'state.json').unlink();run('load')
            self.assertEqual(json.loads((repo/'state.json').read_text()),state)
            self.assertEqual((repo/'source.txt').read_text(),'preserve me')
            git('fetch','origin','stock-state')
            self.assertEqual(git('ls-tree','--name-only','FETCH_HEAD').stdout.strip(),'state.json')

class RunIntegrationTests(unittest.TestCase):
    def run_monitor(self, config, state, sender, now):
        html = '<script>{"apolloState":' + FIXTURE.read_text() + '}</script>'
        def fetch(url):
            if url.endswith('/robots.txt'): return 'User-agent: *\nAllow: /\n'
            if 'pickup-message' in url:
                payload=json.loads(Path('tests/fixtures/apple-pickup.json').read_text())
                # Synthetic in-stock event to verify send/dedup/failure behavior.
                entry=payload['body']['stores'][0]['partsAvailability']['MK2D4QL/A']
                entry.update(pickupDisplay='available',pickupSearchQuote='Disponible hoy')
                return json.dumps(payload)
            return html
        with patch('sys.argv', ['checker.py', '--config', str(config), '--state', str(state)]), \
             patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test-only', 'TELEGRAM_CHAT_ID': 'test-only'}), \
             patch('checker.fetch', side_effect=fetch), patch('checker.telegram', sender), \
             patch('checker.time.sleep'), patch('checker.time.time', return_value=now), \
             patch('builtins.print'):
            return c.main()
    def setup_files(self, root):
        config=json.loads(Path('config.json').read_text())
        path=root/'config.json'; path.write_text(json.dumps(config))
        return path,root/'state.json'
    def test_full_runs_deduplicate_stock_and_health(self):
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as directory:
            config,state=self.setup_files(Path(directory)); sender=Mock(return_value={})
            self.assertEqual(self.run_monitor(config,state,sender,1792843200),0)
            self.assertEqual(sender.call_count,2) # synthetic Apple stock alert + initial coverage
            self.assertEqual(self.run_monitor(config,state,sender,1792846801),0)
            self.assertEqual(sender.call_count,2)
    def test_failed_telegram_not_marked_delivered_then_retried(self):
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as directory:
            config,state=self.setup_files(Path(directory))
            self.assertEqual(self.run_monitor(config,state,Mock(side_effect=RuntimeError('delivery failed')),1792843200),1)
            saved=json.loads(state.read_text())
            self.assertNotIn('last_alert',saved['items']['apple:MK2D4QL/A:pickup:R368'])
            sender=Mock(return_value={})
            self.assertEqual(self.run_monitor(config,state,sender,1792846801),0)
            self.assertEqual(sender.call_count,2)

if __name__=='__main__':unittest.main()
