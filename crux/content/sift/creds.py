"""sift: reading a pile of recovered credential material.

Three scenarios. This is the other half of finding a credential: knowing, at a
glance, **which of the things you just dumped is worth your time**. A domain
hash you can pass is worth more than a bcrypt you will never crack, and both
look like hex to somebody who has not learned the shapes.

The reading problem is format recognition, and it is the one that decides
whether the next two hours go into hashcat or into logging in.
"""

from __future__ import annotations

from ...model import Action, MarkBody, Scenario
from ...targets._fixture import Note, TextBlock

AD = 'Boxes/Active Directory'
PLAYBOOK = 'PEN-200 Playbook'

# --------------------------------------------------------------------------
# 1. Pass it, do not crack it
# --------------------------------------------------------------------------

_NTLM = MarkBody(
    prompt='You dumped local secrets from a Windows host. Mark every line '
           'that changes what you do next.',
    fixture=TextBlock(
        header=('secretsdump.py -sam sam.hive -system system.hive LOCAL',
                '[*] Dumping local SAM hashes (uid:rid:lmhash:nthash)'),
        rows=(
            Note('Administrator:500:aad3b435b51404eeaad3b435b51404ee:'
                 '31d6cfe0d16ae931b73c59d7e0c089c0:::', 'decoy',
                 why='The most attractive name on the screen and an empty '
                     'password: 31d6cfe0d16ae931b73c59d7e0c089c0 is the NT '
                     'hash of the empty string, and it appears here four '
                     'times.'),
            Note('Guest:501:aad3b435b51404eeaad3b435b51404ee:'
                 '31d6cfe0d16ae931b73c59d7e0c089c0:::'),
            Note('svc_backup:1008:aad3b435b51404eeaad3b435b51404ee:'
                 'a0de4d7f81676c3ea9eabcadfd2536f6:::', 'lead',
                 why='The only account here with a real NT hash. And it does '
                     'not need cracking: an NT hash IS the credential for NTLM '
                     'authentication, so pass it straight at the network.'),
            Note('DefaultAccount:503:aad3b435b51404eeaad3b435b51404ee:'
                 '31d6cfe0d16ae931b73c59d7e0c089c0:::'),
        ),
        noise_pool=(
            Note('WDAGUtilityAccount:504:aad3b435b51404eeaad3b435b51404ee:'
                 '31d6cfe0d16ae931b73c59d7e0c089c0:::'),
            Note('[*] Dumping cached domain logon information'),
            Note('[*] Cleaning up...'),
        ),
        noise=(1, 3),
    ),
    actions=(
        Action('Pass `svc_backup` NT hash straight at the network: no '
               'cracking needed.', True,
               'An NT hash **is** the credential for NTLM authentication. '
               '`crackmapexec -H`, `psexec.py -hashes`, `evil-winrm -H` all '
               'take it as it stands, and a service account is exactly the '
               'kind that is reused on other hosts.'),
        Action('Feed every hash to hashcat with `-m 1000` and a big wordlist.',
               why='Sometimes worth starting in the background, never worth '
                   'waiting on. You can authenticate with the hash right now; '
                   'cracking it only gets you a string you did not need.'),
        Action('The Administrator hash is the prize: crack that one first.',
               why='Look at it again. `31d6cfe0d16ae931b73c59d7e0c089c0` is '
                   'the NT hash of the **empty string**, and it appears here '
                   'four times. Those accounts are disabled or password-less, '
                   'and it is the single most recognisable hash in Windows.'),
        Action('The `aad3b435b51404eeaad3b435b51404ee` half is an LM hash '
               'worth attacking, since LM is weak.',
               why='That constant is the LM hash of an empty string, which is '
                   'what modern Windows stores because LM is disabled. It is '
                   'on every line and it is never the finding.'),
    ),
    debrief='**Two constants worth knowing by sight.** '
            '`aad3b435b51404eeaad3b435b51404ee` is an empty LM hash and is on '
            'every modern line; `31d6cfe0d16ae931b73c59d7e0c089c0` is an '
            'empty NT hash, so an account showing it has no password set. '
            'Once both are furniture, the only rows left are the accounts '
            'that actually have one.\n\n'
            'And the habit that saves the most time: **an NT hash does not '
            'need cracking.** It is the authentication material itself. Try '
            'it against the network before you spend an hour on a wordlist.',
)

# --------------------------------------------------------------------------
# 2. Which of these is worth the GPU
# --------------------------------------------------------------------------

_FORMATS = MarkBody(
    prompt='You collected credential material from several places on the '
           'network. Mark the one worth spending offline cracking time on.',
    fixture=TextBlock(
        header=('loot/collected.txt',),
        rows=(
            Note('web/config.php   $2y$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p'
                 '92ldGxad68LJZdL17lhWy', 'decoy',
                 why='bcrypt at cost 10, deliberately slow. Reuse is a real '
                     'argument for wanting it and the arithmetic is still '
                     'against you: orders of magnitude slower per guess than '
                     'the ticket.'),
            Note('kerberoast.txt   $krb5tgs$23$*svc_sql$CORP.LOCAL$'
                 'MSSQLSvc/db01.corp.local*$a1b2c3...', 'lead',
                 why='A service ticket encrypted with the service account '
                     'password. Fast to attack, and those passwords are often '
                     'old, human-chosen and never rotated, which is why '
                     'kerberoasting pays out so often.'),
            Note('shadow.bak       root:$6$xyz$3kPq...:19700:0:99999:7:::',
                 'decoy',
                 why='SHA-512-crypt with thousands of rounds. Also '
                     'deliberately slow, and you already hold a faster target '
                     'on the same screen.'),
            Note('notes.txt        33d81ad509ef34a2635903babb285882'),
        ),
        noise_pool=(
            Note('web/config.php   define("DB_HOST", "localhost");'),
            Note('loot/readme.txt  collected 2026-08-14'),
            Note('shadow.bak       daemon:*:19700:0:99999:7:::'),
        ),
        noise=(1, 3),
    ),
    actions=(
        Action('Crack the Kerberos service ticket: `hashcat -m 13100`, and it '
               'is the one most likely to fall.', True,
               'A `$krb5tgs$` blob is a service ticket encrypted with the '
               'service account password. Those are frequently old, '
               'human-chosen and never rotated, which is why kerberoasting '
               'pays out so often, and cracking it hands you a domain '
               'account.'),
        Action('Crack the bcrypt from the web config: application '
               'credentials get reused.',
               why='`$2y$10$` is bcrypt at cost 10, deliberately slow. Reuse '
                   'is a real argument for wanting it and the arithmetic is '
                   'still against you: this is orders of magnitude slower per '
                   'guess than the ticket above.'),
        Action('Crack the `$6$` root hash out of the shadow backup.',
               why='`$6$` is SHA-512-crypt with thousands of rounds. Also '
                   'deliberately slow, and you already hold a faster target '
                   'on the same screen.'),
        Action('The 32-hex string in notes.txt is an MD5: crack that first, '
               'it is instant.',
               why='Fast to try and worth ten seconds in a lookup, which is '
                   'why it is tempting. But you have no idea what it '
                   'authenticates to: an unlabelled hash with no username and '
                   'no service is a string, not a credential.'),
    ),
    debrief='**Read the prefix, then decide where the GPU goes.** `$2y$` is '
            'bcrypt and `$6$` is SHA-512-crypt: both are deliberately slow '
            'and both are usually a poor use of exam hours. `$krb5tgs$` and '
            '`$krb5asrep$` are fast to attack and are cracked against '
            'passwords humans chose for service accounts years ago, which is '
            'the best return on the screen. A bare 32-hex string might be MD5 '
            'and might be anything; without a username beside it, cracking it '
            'buys you a word.',
)

# --------------------------------------------------------------------------
# 3. Already a credential (crux D9)
# --------------------------------------------------------------------------

_NOT_A_HASH = MarkBody(
    prompt='More material from the same host. Mark anything worth offline '
           'cracking time.',
    fixture=TextBlock(
        header=('loot/second-pass.txt',),
        rows=(
            Note('backup.ps1       $cred = "Summer2025!Rotate"', 'decoy',
                 why='Already a credential. There is nothing to crack: spray '
                     'it at every account and move.'),
            Note('web.config       <add key="ApiKey" value='
                 '"7f2c1e9a4b6d8f03" />', 'decoy',
                 why='A key, not a digest of anything. Cracking recovers an '
                     'input that produced a hash; there is no input behind an '
                     'API key.'),
            Note('id_rsa           -----BEGIN OPENSSH PRIVATE KEY----- '
                 '(no passphrase)', 'decoy',
                 why='ssh2john exists for keys that ARE passphrase-protected. '
                     'This one says it is not, so there is nothing to recover: '
                     'use it.'),
            Note('session.txt      eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyIjoiZ3Vlc3Qi'
                 'fQ.Xy'),
        ),
        noise_pool=(
            Note('loot/second-pass.txt  collected after the pivot'),
            Note('web.config       <compilation debug="true" />'),
        ),
        noise=(1, 2),
    ),
    actions=(
        Action('Nothing here needs cracking. Use them: they are already '
               'credentials.', True,
               'A cleartext password, an unencrypted private key and an API '
               'key are the finished article. Spraying the password at every '
               'account and trying the key against every host beats any '
               'amount of hashcat, and costs minutes.'),
        Action('The API key is 16 hex characters: run it through hashcat in '
               'case it is a hash.',
               why='It is a key, not a digest of anything. Cracking is for '
                   'recovering an input that produced a hash; there is no '
                   'input behind an API key.'),
        Action('The private key has no passphrase, so run `ssh2john` on it '
               'anyway to confirm.',
               why='`ssh2john` exists for keys that **are** passphrase-'
                   'protected. This one says it is not, so there is nothing '
                   'to recover: use it.'),
        Action('Crack the JWT signing secret so you can forge tokens.',
               why='Occasionally the right move, and it is a real technique. '
                   'But that token decodes to a guest session, and you have a '
                   'cleartext admin-looking password two lines above it. '
                   'Forge tokens when the easy credential fails, not before.'),
    ),
    debrief='**Cracking is what you do when you cannot use the thing '
            'directly.** A screen of cleartext passwords, unencrypted private '
            'keys and API keys has nothing to crack on it, and the correct '
            'answer is to mark nothing and start using them. The most '
            'expensive mistake in this track is not failing to crack a hash, '
            'it is spending an hour cracking something you were already '
            'holding the answer to.',
)

SCENARIOS = [
    Scenario(id='sift-creds-ntlm', track='sift', tier='graded', order=910,
             title='A SAM dump, and one account with a password',
             body=_NTLM, waypoint='crack-classify', hone=('hashcat',),
             source=f'{AD}/HackTheBox/Cicada/Cicada - Writeup.md'),
    Scenario(id='sift-creds-formats', track='sift', tier='graded', order=920,
             title='Four kinds of hash, one worth the GPU',
             body=_FORMATS, waypoint='crack-classify',
             hone=('hashcat', 'john'),
             source=f'{PLAYBOOK}/10 - Phase 8 - Password Attacks & Cracking.md'),
    Scenario(id='sift-creds-cleartext', track='sift', tier='graded', order=930,
             title='Material that does not need cracking',
             body=_NOT_A_HASH, waypoint='crack-classify', hone=('hashcat',),
             source=f'{PLAYBOOK}/10 - Phase 8 - Password Attacks & Cracking.md'),
]
