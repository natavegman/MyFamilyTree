import sys, json, base64, email, email.policy, os
raw = base64.b64decode(json.load(open(sys.argv[1]))['content'])
msg = email.message_from_bytes(raw, policy=email.policy.default)
out = sys.argv[2]; os.makedirs(out, exist_ok=True)
for part in msg.walk():
    fn = part.get_filename()
    if fn:
        data = part.get_payload(decode=True) or b''
        p = os.path.join(out, fn)
        open(p,'wb').write(data)
        print(p, len(data))
