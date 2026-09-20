import sys, json, base64, email, email.policy
def show(path):
    raw = base64.b64decode(json.load(open(path))['content'])
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    print('SUBJ:', msg.get('Subject'))
    print('FROM:', msg.get('From'), '| TO:', msg.get('To'), '| DATE:', msg.get('Date'))
    for part in msg.walk():
        ct = part.get_content_type()
        fn = part.get_filename()
        if fn:
            print(f'--- ATTACH: {fn} ({ct}, {len(part.get_payload(decode=True) or b"")} bytes)')
        elif ct == 'text/plain':
            print('--- BODY ---')
            print(part.get_content())
if __name__ == '__main__':
    show(sys.argv[1])
