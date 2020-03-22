#!/usr/local/bin/python3
'''
    Teachin basic concept of recursion.
'''

def add_one(val):
    if val <= 10000:
        print("Adding one to {}".format(val))
        val = val + 1

    if val == 10:
        print("10!")

    else:
        add_one(val)

if __name__ == "__main__":
    value = 1

    print("Value has finally readched:")
    add_one(value)
    
