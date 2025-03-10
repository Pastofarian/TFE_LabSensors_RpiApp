import unittest
import json
from rpi_app import app

class RpiBackendTestCase(unittest.TestCase):
    def setUp(self):
        # set up test mode and test client
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_main_page(self):
        # test main page returns welcome text
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Bienvenue dans l'app de mesure du labo acoustique", response.data)

    def test_lab_datas_node_7(self):
        # test /lab_datas endpoint for node 7
        response = self.client.get('/lab_datas?node=7')
        self.assertEqual(response.status_code, 200)
        # check for known text in html (for exemple 'cellule')
        self.assertIn(b"cellule", response.data)

    def test_live_data(self):
        # test /live_data returns json with expected keys
        response = self.client.get('/live_data?node=7')
        self.assertEqual(response.status_code, 200)
        try:
            data = json.loads(response.data)
            self.assertIn("temp", data)
            self.assertIn("hum", data)
            self.assertIn("pres", data)
        except json.JSONDecodeError:
            self.fail("response is not valid json")

    def test_lab_datas_db(self):
        # test /lab_datas_db returns html page with expected content
        response = self.client.get('/lab_datas_db?node=7')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"dashboard", response.data)

    def test_to_plotly(self):
        # test /to_plotly returns path to plotly graph
        response = self.client.get('/to_plotly')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"/static/plotly_graph.html", response.data)

if __name__ == '__main__':
    unittest.main()

