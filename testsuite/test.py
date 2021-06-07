import unittest
import bytehook

class TestBytehook(unittest.TestCase):
    def test_hook(self):
        def list_empty_function():
            alist = []
            return bool(alist)

        self.assertEqual(list_empty_function(), False)

        def inject_element(locals_, globals_):
            locals_['alist'].append(1)

        bytehook.hook(list_empty_function, 2, inject_element, True)
        self.assertEqual(list_empty_function(), True)

    def test_hook_modifyRetval(self):
        def add(a, b):
            return a + b

        self.assertEqual(add(2, 3), 5)
        bytehook.hook_modifyRetval(add, 10)
        self.assertEqual(add(2,3), 10)

if __name__ == '__main__':
    unittest.main()
