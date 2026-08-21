"""sift: reading a directory dump.

Three scenarios. Directory output is long, uniform, and almost entirely
administrative metadata, and the findings in it are things a **person** typed:
a password parked in a description field, an account flagged in a way nobody
meant to leave, a naming convention that tells you what a service does.

This is where 40 of the 70 exam points live, and the reading habit that pays
is to stop looking at account names and start looking at free-text fields.
"""

from __future__ import annotations

from ...model import Action, MarkBody, Scenario
from ...targets._fixture import DirUser, LdapUsers

AD = 'Boxes/Active Directory'
PLAYBOOK = 'PEN-200 Playbook'

_DESCRIPTION = MarkBody(
    prompt='An anonymous LDAP dump of domain users. Mark every line that '
           'changes what you do next.',
    fixture=LdapUsers(
        domain='DC=harbord,DC=local',
        noise=(6, 9),
        users=(
            DirUser('michael.wrightson', 'Account created by IT'),
            DirUser('david.orelious',
                    'Just in case I forget my password is aRt$Lp#7t*VQ!3',
                    kind='lead',
                    why='Somebody wrote a working password into a '
                        'world-readable field. Validate it against every '
                        'account, not only this one: reuse is the norm.'),
            DirUser('emily.oscars', 'Password must be changed on next logon',
                    kind='decoy',
                    why='The standard text an administrator types when setting '
                        'a flag, not a hint about the value. It reads like a '
                        'lead and is boilerplate.'),
            DirUser('john.smoulder', ''),
        ),
    ),
    actions=(
        Action('Take the password out of the description and validate it '
               'against the whole user list.', True,
               'Somebody wrote a working password into a world-readable '
               'field. Validate it before anything else, and validate it '
               'against every account rather than only the one it belongs to, '
               'because reuse is the norm.'),
        Action('Target `emily.oscars`: the description says the password must '
               'be changed, so it is probably still the default.',
               why='The instructive wrong answer. That string is the standard '
                   'text an administrator types when they set a flag, not a '
                   'hint about the value. It reads like a lead and is '
                   'boilerplate.'),
        Action('Feed the user list to a password spray with a seasonal '
               'wordlist.',
               why='Noisy, slow, and locks accounts out. You have a real '
                   'credential sitting on this screen; spend it before you '
                   'start guessing.'),
        Action('Kerberoast every account and crack the tickets offline.',
               why='A good technique that needs a domain credential you do '
                   'not have yet. It is the step after this one, not this '
                   'one.'),
    ),
    debrief='**Read the free-text fields, not the account names.** '
            '`description`, `info`, `comment` and `userPrincipalName` are '
            'where humans write things, and humans write passwords into them '
            'when they are in a hurry. Anonymous or low-privilege LDAP reads '
            'expose them to everybody in the domain.',
)

_FLAGS = MarkBody(
    prompt='A domain user dump taken with a low-privilege account. Mark every '
           'line that changes what you do next.',
    fixture=LdapUsers(
        domain='DC=corp,DC=local',
        noise=(6, 9),
        users=(
            DirUser('svc_web', 'IIS application pool', flags='DONT_REQ_PREAUTH',
                    kind='lead',
                    why='DONT_REQ_PREAUTH means Kerberos will hand encrypted '
                        'material for this account to anyone who asks. It '
                        'costs nothing, it is silent, and it needs no '
                        'credential at all.'),
            DirUser('svc_backup', 'Nightly backup job', flags='NORMAL_ACCOUNT',
                    kind='decoy',
                    why='Right family of attack, wrong row: NORMAL_ACCOUNT is '
                        'the default flag on every user in the directory, and '
                        'nothing here says it has an SPN.'),
            DirUser('a.mcintyre', 'Domain Admin - do not disable',
                    kind='decoy',
                    why='The most attractive line and the least actionable. It '
                        'tells you where you are going, not how to get there, '
                        'and a description is not authoritative about group '
                        'membership anyway.'),
        ),
    ),
    actions=(
        Action('AS-REP roast `svc_web`: pull its encrypted blob without any '
               'credential and crack it offline.', True,
               '`DONT_REQ_PREAUTH` means Kerberos will hand out material '
               'encrypted with that account password to anyone who asks. It '
               'costs nothing, it is silent, and it needs no credential at '
               'all.'),
        Action('Target `a.mcintyre`, whose description says Domain Admin.',
               why='The most attractive line and the least actionable. '
                   'Knowing who the Domain Admin is tells you where you are '
                   'going, not how to get there, and a description is not '
                   'even authoritative about group membership.'),
        Action('Kerberoast `svc_backup`, since service accounts have SPNs.',
               why='The right family of attack on the wrong row. It is a '
                   'plausible service account, but `NORMAL_ACCOUNT` is the '
                   'default flag on every user in the directory, and nothing '
                   'here says it has an SPN.'),
        Action('Note that service accounts exist and spray a common password '
               'across all of them.',
               why='Lockout policies exist, and this screen contains a free, '
                   'silent, guaranteed-response attack you have not used.'),
    ),
    debrief='**`userAccountControl` is where accounts admit things.** '
            '`DONT_REQ_PREAUTH` is AS-REP roastable, '
            '`TRUSTED_FOR_DELEGATION` is worth a whole attack path, and '
            '`PASSWD_NOTREQD` means what it says. `NORMAL_ACCOUNT` is on '
            'everybody. Learn the two or three that matter and this output '
            'reads itself.',
)

_QUIET_DIR = MarkBody(
    prompt='A domain user dump taken with a low-privilege account. Mark every '
           'line that changes what you do next.',
    fixture=LdapUsers(
        domain='DC=meridian,DC=local',
        noise=(7, 10),
        users=(
            DirUser('svc_sched', 'Scheduled tasks', flags='NORMAL_ACCOUNT',
                    kind='decoy',
                    why='A name that looks like a service account is not '
                        'evidence of an SPN, and Kerberoasting needs a domain '
                        'credential you do not have yet.'),
            DirUser('p.nguyen', 'Finance - starter 2024', kind='decoy',
                    why='A story built out of a date in a description. It '
                        'could be true, and nothing on this screen supports '
                        'it.'),
        ),
    ),
    actions=(
        Action('Nothing here. Keep the user list and move on to something '
               'that produces a credential.', True,
               'Correct. Every description is administrative boilerplate and '
               'every flag is the default. The dump is still valuable, but as '
               'a **list of names** for later, not as a finding now.'),
        Action('Spray `Welcome2026!` across the list: someone always reuses '
               'the season.',
               why='Sometimes true, and it is the step people reach for at '
                   'exactly this moment. It also trips lockout policies and '
                   'is the loudest thing you can do in a domain. It is a '
                   'considered decision, not a reflex when a screen '
                   'disappoints you.'),
        Action('`svc_sched` is a service account, so Kerberoast it.',
               why='Kerberoasting needs a domain credential and an SPN. The '
                   'name looking like a service account is not evidence of '
                   'either.'),
        Action('`p.nguyen` joined recently, so the account probably still has '
               'its starting password.',
               why='A story built out of a date in a description. It could be '
                   'true and nothing on this screen supports it.'),
    ),
    debrief='**A dump with nothing in it is still worth having.** The names '
            'become your spray list, your Kerberoast targets and your '
            'username convention once you have a credential from somewhere '
            'else. Marking nothing here is not saying the output was useless, '
            'it is saying it contains no lead to act on **now**.',
)

SCENARIOS = [
    Scenario(id='sift-ldap-description', track='sift', tier='graded',
             order=610, title='Domain users, and a field somebody typed into',
             body=_DESCRIPTION, waypoint='ad-harvest', hone=('ldapsearch',),
             source=f'{AD}/HackTheBox/Cicada/Cicada - Writeup.md'),
    Scenario(id='sift-ldap-flags', track='sift', tier='graded', order=620,
             title='Domain users, and one account control flag',
             body=_FLAGS, waypoint='ad-asrep', hone=('ldapsearch',),
             source=f'{PLAYBOOK}/08 - Phase 6 - Active Directory.md'),
    Scenario(id='sift-ldap-quiet', track='sift', tier='graded', order=630,
             title='Domain users, all of them ordinary',
             body=_QUIET_DIR, waypoint='ad-enum', hone=('ldapsearch',),
             source=f'{PLAYBOOK}/08 - Phase 6 - Active Directory.md'),
]
