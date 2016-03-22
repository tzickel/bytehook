from __future__ import print_function
import bytehook


def test():
    for i in range(4):
        print(i)


if __name__ == "__main__":
    print('1st try')
    test()

    def odd_or_even(locals, globals):
        if locals['i'] % 2:
            print('odd')
        else:
            print('even')

    hookid = bytehook.hook(test, lineno=2, insert_func=odd_or_even, with_state=True)
    print('2nd try')
    test()
    bytehook.disable_hookpoint(hookid)
    print('3rd try')
    test()
