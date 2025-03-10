import re
from aprslib import base91
from aprslib.exceptions import ParseError
from aprslib.parsing import logger

__all__ = [
    'parse_comment_telemetry',
    'parse_telemetry_config',
    'parse_telemetry_report'
]


def parse_comment_telemetry(text):
    """
    Looks for base91 telemetry found in comment field
    Returns [remaining_text, telemetry]
    """
    parsed = {}
    match = re.findall(r"^(.*?)\|([!-{]{4,14})\|(.*)$", text)

    if match and len(match[0][1]) % 2 == 0:
        text, telemetry, post = match[0]
        text += post

        temp = [0] * 7
        for i in range(7):
            temp[i] = base91.to_decimal(telemetry[i*2:i*2+2])

        parsed.update({
            'telemetry': {
                'seq': temp[0],
                'vals': temp[1:6]
                }
            })

        if temp[6] != '':
            parsed['telemetry'].update({
                'bits': "{0:08b}".format(temp[6] & 0xFF)[::-1]
                })

    return (text, parsed)


def parse_telemetry_config(body):
    parsed = {}

    match = re.findall(r"^(PARM|UNIT|EQNS|BITS)\.(.*)$", body)
    if match:
        logger.debug("Attempting to parse telemetry-message packet")
        form, body = match[0]

        parsed.update({'format': 'telemetry-message'})

        if form in ["PARM", "UNIT"]:
            vals = body.rstrip().split(',')[:13]

            for val in vals:
                # Some clients allow for longer PARM names. We'll allow up 30 per field
                # https://github.com/PhirePhly/aprs_notes/blob/master/telemetry_format.md#
                if not re.match(r"^(.{1,30}|)$", val):
                    raise ParseError("Incorrect format of %s (name too long?)" % form)

            defvals = [''] * 13
            defvals[:len(vals)] = vals

            parsed.update({
                't%s' % form: defvals
                })
        elif form == "EQNS":
            # From the spec. "The list can terminate after any field." so the EQNS field may not be 15 chars and could
            # contain extraneous garbage at the end.  Technically the packet is invalid, but we'll attempt to remove them.
            eqns = body.rstrip('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz .').split(',')[:15]
            teqns = [0, 1, 0] * 5

            for idx, val in enumerate(eqns):
                # Make sure there's no whitespace preceeding the data
                val = val.lstrip();
                if not re.match(r"^([-]?\d*\.?\d+|)$", val):
                    raise ParseError("Value %s at %d is not a number in %s" % (val, idx+1, form))
                else:
                    try:
                        val = int(val)
                    except:
                        val = float(val) if val != "" else 0

                    teqns[idx] = val

            # group values in 5 list of 3
            teqns = [teqns[i*3:(i+1)*3] for i in range(5)]

            parsed.update({
                't%s' % form: teqns
                })
        elif form == "BITS":
            # From the spec. The projec title should be no more than 23 characters but can be as long as 183.
            match = re.findall(r"^([01]{8}),(.{0,183})$", body.rstrip('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz .'))
            if not match:
                raise ParseError("Incorrect format of %s (title too long?)" % form)

            bits, title = match[0]

            parsed.update({
                't%s' % form: bits,
                'title': title.strip(' ')
                })

    return (body, parsed)


def parse_telemetry_report(text):
    parsed = {}
    rest = ""

    match = re.findall(r"(^#\d{1,3},(\d+(\.\d+)?,){5}[01]{8}$)", text)

    if match:
        logger.debug("Attempting to parse telemetry-message packet")

        temp = text.split(",")
        parsed.update({'format': 'telemetry-report'})

        seq = int(temp[0].replace('#', ''))
        values = list(map(float, temp[1:6]))

        parsed.update({
            'telemetry': {
                'seq': seq,
                'vals': values,
                'bits': temp[6]
            }
        })
    else:
        rest = text

    return rest, parsed
