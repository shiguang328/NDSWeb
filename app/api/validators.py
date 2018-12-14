import re
import uuid
import warnings
from .errors import bad_request

from wtforms.compat import string_types, text_type


class ValidationError(ValueError):
    """
    Raised when a validator fails to validate its input.
    """
    def __init__(self, message='', *args, **kwargs):
        ValueError.__init__(self, message, *args, **kwargs)


class Regexp(object):
    """
    Validates the field against a user provided regexp.

    :param regex:
        The regular expression string to use. Can also be a compiled regular
        expression pattern.
    :param flags:
        The regexp flags to use, for example re.IGNORECASE. Ignored if
        `regex` is not a string.
    :param message:
        Error message to raise in case of a validation error.
    """
    def __init__(self, regex, flags=0, message=None):
        if isinstance(regex, string_types):
            regex = re.compile(regex, flags)
        self.regex = regex
        self.message = message

    def __call__(self, value, message=None):
        match = self.regex.match(value or '')
        if not match:
            # if message is None:
            #     if self.message is None:
            #         message = 'Invalid input.'
            #     else:
            #         message = self.message

            # raise ValidationError(message)
            return bad_request(self.message)
        # return match
        # return True


class IPAddress(object):
    """
    Validates an IP address.

    :param ipv4:
        If True, accept IPv4 addresses as valid (default True)
    :param ipv6:
        If True, accept IPv6 addresses as valid (default False)
    :param message:
        Error message to raise in case of a validation error.
    """
    def __init__(self, ipv4=True, ipv6=False, message=None):
        if not ipv4 and not ipv6:
            raise ValueError('IP Address Validator must have at least one of ipv4 or ipv6 enabled.')
        self.ipv4 = ipv4
        self.ipv6 = ipv6
        self.message = message

    def __call__(self, form, field):
        value = field.data
        valid = False
        if value:
            valid = (self.ipv4 and self.check_ipv4(value)) or (self.ipv6 and self.check_ipv6(value))

        if not valid:
            message = self.message
            if message is None:
                message = field.gettext('Invalid IP address.')
            raise ValidationError(message)

    @classmethod
    def check_ipv4(cls, value):
        parts = value.split('.')
        if len(parts) == 4 and all(x.isdigit() for x in parts):
            numbers = list(int(x) for x in parts)
            return all(num >= 0 and num < 256 for num in numbers)
        return False

    @classmethod
    def check_ipv6(cls, value):
        parts = value.split(':')
        if len(parts) > 8:
            return False

        num_blank = 0
        for part in parts:
            if not part:
                num_blank += 1
            else:
                try:
                    value = int(part, 16)
                except ValueError:
                    return False
                else:
                    if value < 0 or value >= 65536:
                        return False

        if num_blank < 2:
            return True
        elif num_blank == 2 and not parts[0] and not parts[1]:
            return True
        return False


class HostnameValidation(object):
    """
    Helper class for checking hostnames for validation.

    This is not a validator in and of itself, and as such is not exported.
    """
    hostname_part = re.compile(r'^(xn-|[a-z0-9]+)(-[a-z0-9]+)*$', re.IGNORECASE)
    tld_part = re.compile(r'^([a-z]{2,20}|xn--([a-z0-9]+-)*[a-z0-9]+)$', re.IGNORECASE)

    def __init__(self, require_tld=True, allow_ip=False):
        self.require_tld = require_tld
        self.allow_ip = allow_ip

    def __call__(self, hostname):
        if self.allow_ip:
            if IPAddress.check_ipv4(hostname) or IPAddress.check_ipv6(hostname):
                return True

        # Encode out IDNA hostnames. This makes further validation easier.
        try:
            hostname = hostname.encode('idna')
        except UnicodeError:
            pass

        # Turn back into a string in Python 3x
        if not isinstance(hostname, string_types):
            hostname = hostname.decode('ascii')

        if len(hostname) > 253:
            return False

        # Check that all labels in the hostname are valid
        parts = hostname.split('.')
        for part in parts:
            if not part or len(part) > 63:
                return False
            if not self.hostname_part.match(part):
                return False

        if self.require_tld:
            if len(parts) < 2 or not self.tld_part.match(parts[-1]):
                return False

        return True


class Email(object):
    """
    Validates an email address. Note that this uses a very primitive regular
    expression and should only be used in instances where you later verify by
    other means, such as email activation or lookups.

    :param message:
        Error message to raise in case of a validation error.
    """

    user_regex = re.compile(
        r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*\Z"  # dot-atom
        r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-\011\013\014\016-\177])*"\Z)',  # quoted-string
        re.IGNORECASE)

    def __init__(self, message=None):
        self.message = message
        self.validate_hostname = HostnameValidation(
            require_tld=True,
        )

    def __call__(self, value):

        message = self.message
        if message is None:
            message = 'Invalid email address.'

        if not value or '@' not in value:
            # raise ValidationError(message)
            return bad_request(message)

        user_part, domain_part = value.rsplit('@', 1)

        if not self.user_regex.match(user_part):
            # raise ValidationError(message)
            return bad_request(message)

        if not self.validate_hostname(domain_part):
            # raise ValidationError(message)
            return bad_request(message)


class Length(object):
    """
    Validates the length of a string.

    :param min:
        The minimum required length of the string. If not provided, minimum
        length will not be checked.
    :param max:
        The maximum length of the string. If not provided, maximum length
        will not be checked.
    :param message:
        Error message to raise in case of a validation error. Can be
        interpolated using `%(min)d` and `%(max)d` if desired. Useful defaults
        are provided depending on the existence of min and max.
    """
    def __init__(self, min=-1, max=-1, message=None):
        assert min != -1 or max != -1, 'At least one of `min` or `max` must be specified.'
        assert max == -1 or min <= max, '`min` cannot be more than `max`.'
        self.min = min
        self.max = max
        self.message = message

    def __call__(self, value, min=-1, max=-1, fieldName='Field'):
        if min == -1:
            min = self.min
        if max == -1:
            max = self.max

        l = value and len(value) or 0
        if l < min or max != -1 and l > max:
            message = self.message
            if message is None:
                if max == -1:
                    message = '%s must be at least %d characters long.' % (fieldName, min)
                elif min == -1:
                    message = '%s cannot be longer than %d characters.' % (fieldName, max)
                else:
                    message = '%s must be between %d and %d characters long.' % (fieldName, min, max)

            return bad_request(message)


def Require(data_json, fields):
    for field in fields:
        if not data_json.get(field):
            return bad_request('%s is required.' % field)


validate_email = Email()
validate_username = Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                           'Format error, username must have only letters, numbers, dots or underscores.')
validate_length = Length(6, 32)
validate_require = Require


if __name__ == '__main__':
    # print(validate_email('12321@123'))
    # print(validate_email('24132@qq.com'))
    # print(validate_username('1233432'))
    # print(validate_username('liuzhipeng123'))
    print(validate_length('123'))
