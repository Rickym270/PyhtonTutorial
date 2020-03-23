#!/usr/local/bin/python3

class Firewall(object):
    def __init__(self):
        print("Firewall object has been created")
        verified = False

    def __checkIP(self, ip):
        print("In private method")
        print("The IP that's about to be checked is the following: {}".format(ip))
        import re

        ip_regex_str = "(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"

        ip_regex = re.compile(ip_regex_str)
        ver = re.match(ip_regex, ip)
        return bool(ver)

    def checkIP(self, ip):
        print("In public method")
        return self.__checkIP(ip)

if __name__ == "__main__":
    fwObj1 = Firewall()

    ip = "172.16.47.48"
    ip_ver = fwObj1.checkIP(ip)

    print(ip_ver)
