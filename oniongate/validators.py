"""
Helper functions for validating API input
"""
import re
import ipaddress

from flask import current_app


def is_onion_address(onion_address):
    """
    Return onion_address if valid, otherwise return false.
    """
    return re.match(r"^[a-z0-9]{16}.onion$", onion_address) is not None


def label(label):
    """Validate a DNS label"""
    if not is_valid_label(label):
        raise ValueError("{} is not a valid DNS label".format(label))
    return label


def is_valid_label(label, hostname=False):
    """
    Validate a DNS label
    """
    regex = "(?!-)[A-Z\d\-\_]{1,63}(?<!-)$"
    if hostname:
        regex = regex.replace("\_", "") # Underscores are not allowed in hostnames
    return re.compile(regex, re.IGNORECASE).match(label) is not None


def is_valid_hostname(hostname):
    """
    Check if a hostname is valid and is not an IP address.
    """
    if len(hostname) > 255:
        return False

    # must be not all-numeric, so that it can't be confused with an IP address
    if re.match(r"[\d.]+$", hostname):
        return False

    return all(is_valid_label(x, hostname=True) for x in hostname.split("."))

def domain_name(domain_name_str):
    """
    Return the label and zone if valid, raise an exception in any other case.
    """
    if not domain_name_str:
        raise ValueError("You must specify a domain name")

    is_subdomain = '.' not in domain_name_str
    if domain_name_str[-1] == ".":
        # Strip one dot from the right if it is present
        domain_name_str = domain_name_str[:-1]
    is_valid = is_valid_hostname(domain_name_str)

    if is_subdomain:
        if not is_valid:
            raise ValueError("{} is not a valid sub-domain name.".format(domain_name_str))

        # We enforce a minimum subdomain length to avoid subdomains like
        # wwww. or mail. being registered.
        min_subdomain_len = current_app.config["MIN_SUBDOMAIN_LENGTH"]
        if len(domain_name_str) < min_subdomain_len:
            raise ValueError("The subdomain must be at least {} "
                             "characters long.".format(min_subdomain_len))

        if domain_name_str in current_app.config["DOMAIN_BLACKLIST"]:
            raise ValueError("This subdomain is not allowed")

        # This looks like a valid subdomain, return the label and zone.
        return {
                'label': domain_name_str.lower(),
                'zone' : current_app.config["SUBDOMAIN_HOST"].lower()
        }

    else:
        # The user provided a domain name, check if it is valid FQDN
        # We don't accept domains without a TLD.
        if not is_valid or  "." not in domain_name_str:
            raise ValueError("{} is not a valid domain name".format(domain_name_str))

        if domain_name_str.startswith("www."):
            raise ValueError("The domain name should not include the www. label")

        if current_app.config.get("FQDN_REGISTRATION_CLOSED"):
            # XXX: It's important not to let other users register a subdomain on someone else's
            #      domain. But we also need to prevent users from trying to register domains
            #      such as co.uk which would all registrations for that TLD.

            # I'm going to disable automatic registration of FQDN for now. We can add domains
            # manually.
            raise ValueError("It is not possible to register a full domain at the present time. "
                             "Please choose a sub-domain or contact the administrators")

        if domain_name_str in current_app.config["DOMAIN_BLACKLIST"]:
            raise ValueError("The domain is not allowed")

        # This FQDN is at the root of a zone, the label is None
        return {
                'label': None,
                'zone' : domain_name_str.lower()
        }

def ip_address(ip_address_str):
    """
    Validate that an address is a valid public IPv4 or IPv6 address.

    Returns an IPv4Address or IPv6Address object.
    """
    ip = ipaddress.ip_address(ip_address_str)
    if ip.is_private:
        raise ValueError("Only public IP addresses are valid")
    return ip


def allowed_dns_record_type(record_type):
    """
    Validate that a valid and enabled DNS record type was provided.
    """
    record_type = record_type.strip().upper()
    allowed_types = current_app.config["ALLOWED_DNS_RECORD_TYPES"]

    if record_type not in allowed_types:
        raise ValueError(
            "{} is not an allowed DNS record type. Only types {} are "
             "allowed".format(record_type, ", ".join(allowed_types))
        )
    return record_type
