Incidents are going to happen.

> "The only way to make sense out of change is to plunge into it, move with it, and join the dance." -Alan Watts

## What is an incident?
At it's core, an incident is a malfunction or unexpected behavior in our system that has the potential to critically affect the company or our users. 

At our scale, an incident mandates the attention of all engineers.

If an issue is severe enough that everyone should know ASAP, it's an incident.

## When to raise an incident

**When in doubt, raise an incident.** We'd much rather have declared an incident which turned out not to be an incident. Many incidents take too long to get called, or are missed completely because someone didn't ring the alarm when they had a suspicion something was wrong.

To declare an incident, send a message in Slack #development with @channel. If an engineering lead believes this is a critical incident, create a new channel named `incident-<short_descriptor>`. Point to the new channel in #development. In the new channel, describe what is going on.

Some things that should definitely be an incident

- `app.agentops.ai` being completely unavailable (not just for you)
- No traces are recorded
- Data is lost or inaccessible
- Various alerts defined as critical, such as disk space full, OOM or >5 minute ingestion lag

Things that _shouldn’t_ be an incident

- Metrics being calculated incorrectly
- Spans being < 5 minutes behind
- Expected disruption which happens as part of scheduled maintenance

Ask yourself, "Is this issue impacting one customer severely enough we would lose them, or many customers enough they'll lose trust?" If so, it's an incident.

### Security-specific guidance

Security incidents can have far-reaching consequences and should always be treated with urgency. 

**Contact leadership immediately**

Some examples of security-related issues that warrant raising an incident include:

- Unauthorized access to systems, data, or user accounts
- Detection of malware, ransomware, or other malicious software on company systems
- Suspicious activity on production infrastructure, such as unexpected user logins, privilege escalations, or resource consumption spikes
- Discovery of exposed credentials, sensitive data, or secrets in logs, repositories, or public forums
- Receiving a credible report of a vulnerability or exploit affecting company systems

**When in doubt, err on the side of caution and raise the incident and escalate early!** Better to be safe than sorry.

### Incident severity

Please refer to the following guidance when choosing the severity for your incident. If you are unsure, it's usually better to over-estimate than under-estimate!

#### Minor

A minor-severity incident does not usually require paging people, and can be addressed within normal working hours. It is higher priority than any bugs however, and should come before sprint work.

Examples

- Broken non-critical functionality, with no workaround. Not on the critical path for customers.
- Performance degradation. Not an outage, but our app is not performing as it should. For instance, growing (but not yet critical) ingestion lag.
- A memory leak in a database or feature. With time, this could cause a major/critical incident, but does not usually require _immediate_ attention.
- A low-risk security vulnerability or non-critical misconfiguration, such as overly permissive access on a non-sensitive resource

If not dealt with, minor incidents can often become major incidents. Minor incidents are usually OK to have open for a few days, whereas anything more severe we would be trying to resolve ASAP.

#### Major

A major incident usually requires paging people, and should be dealt with _immediately_. They are usually opened when key or critical functionality is not working as expected.

Major incidents often become critical incidents if not resolved in a timely manner.

Examples

- Customer signup is broken
- Significantly elevated error rate
- A Denial of Service (DoS) attack or other malicious activity that affects system availability
- Discovery of exposed sensitive data (e.g., credentials, secrets) that could lead to a security breach if not remediated

#### Critical

An incident with very high impact on customers, and with the potential to existentially affect the company or reduce revenue.

Examples

- OTEL collector is completely down
- A data breach, or loss of data
- Span ingestion totally failing - we are losing spans
- Discovery of an active security exploit, such as a compromised user account or system
- Detection of ransomware, malware, or unauthorized modifications to production systems

## What happens during an incident?

The person who raised the incident is the incident lead. It’s their responsibility to:

- Make sure the right people are notified.
- Take notes in the incident channel. This should include timestamps, and is a brain dump of everything that we know, and everything that we are or have tried. This will give us much more of an opportunity to learn from the incident afterwards.

If the person who raised the incident is not the best person to debug the issue, as soon as a more senior or relevant person is involved in the situation, they should assume the role of incident lead.

As the situation develops, the incident lead is responsible for assigning tasks and excuting the right actions to resolve the incident.

### Customer communications

Significant incidents such as the app being partially or fully non-operational, as well as ingestion delays of 30 minutes or longer should be clearly communicated to our customers. They should get to know what is going on and what we are doing to resolve it.

When handling a security incident, please align with the incident responder team in the incident slack channel about public communication of security issues. E.g. it could not make sense to immediately communicate an attack publicly, as this could make the attacker aware that we are investigating already. This could it make harder for us to stop this attack for good.

If an early communication is outweighing those kind of downsides or helps our customers if affected. This decision should be made by leadership. If you believe early communication is paramount, please express this. Leadership will organize and write these communications for you, so please let them know if this is needed. Contact Alex or Braelyn.


## When does an incident end?

When we’ve identified the root cause of the issue and put a fix in place. The incident lead can end the incident by announcing it in the incident channel. Make sure to also mark the incident as resolved on channel description. Leadership will make the final call that an incident has ended.

## What happens after an incident? (Incident analysis)

1. Schedule an incident review, invite everyone who participated in the incident.
2. Add a new document to the incidents analysis workspace in Atuin using [this template](https://www.atlassian.com/incident-management/postmortem/templates#timeline).
3. Hold the meeting.
4. Record all information and document in such a way as to learn and grow.

All critical incidents should have a PR in the post-mortem repository + a scheduled meeting. All major incidents should have a PR in the post-mortem repository, and optionally a scheduled meeting.

## Blame

Incidents are never the failure of one person. At minimum, it is a failure of process. Blame should never be attributed to an individual. 

If an incident is downstream from your changes, the best thing you can do is alert the team and work together to resolve it. _You will never be reprimanded for handling an incident properly, even if you played a part in its origin._

**Never point blame at others, this only leads to defensive behavior, making investigating and resolving the incident more difficult.**

_Thanks to [Incident Review and Postmortem Best Practices](https://blog.pragmaticengineer.com/postmortem-best-practices/) from Pragmatic Engineer_