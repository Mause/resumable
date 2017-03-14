from resumable import split, rebuild

import requests


def get(s):
    return s


@rebuild
def example(_):
    print('this is a good start')

    value = split(requests.get, 'first')('http://ms.mause.me')

    print(value.text)

    value = split(lambda: 'hello', 'second')()

    print('hello', value)

    return split(get)('otherworldly')


def main():
    arg = None
    for name, func in example.items():
        arg = func(arg)
        print(arg)


if __name__ == '__main__':
    main()
