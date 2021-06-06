import unittest


class TestBytehook(unittest.TestCase):
    def test_hook(self):
        import bytehook

        def list_empty_function():
            alist = []
            return bool(alist)

        self.assertEqual(list_empty_function(), False)

        def inject_element(locals_, globals_):
            locals_['alist'].append(1)

        bytehook.hook(list_empty_function, 1, inject_element, True)
        # import pdb
        # pdb.set_trace()
        self.assertEqual(list_empty_function(), True)


if __name__ == '__main__':
    unittest.main()
