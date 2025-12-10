# Security breach response procedure

## Purpose

This document guides Controllers in responding to security incidents affecting Flowintel deployments. It covers both technical breaches (unauthorised access, data exfiltration) and organisational breaches (policy violations, insider misuse).

## 1. Notification obligations

### GDPR (CSIRT, private sector, non-LEA deployments)

**To supervisory authority:**
- Notify within **72 hours** of becoming aware of a breach
- Only required if the breach is **likely to result in a risk** to individuals' rights and freedoms
- Use official breach notification channels

**To affected individuals:**
- Notify **without undue delay** when breach likely results in **high risk** to their rights
- Must include: nature of breach, contact point, likely consequences, measures taken
- Not required if: data encrypted, subsequent measures taken to reduce risk, or disproportionate effort (then public communication instead)

**Example:** A CSIRT using Flowintel to track network incidents discovers unauthorised access exposing names and email addresses of 150 employees. Risk assessment: medium (spam/phishing possible, no financial data exposed). Action: notify supervisory authority within 72 hours; individual notification not required unless risk escalates.

---

### Law enforcement (LEA deployments)

**To supervisory authority:**
- Notify **without undue delay** (no specific time limit, but document reasons for any delay)
- Required for all breaches affecting personal data processed for law enforcement purposes
- Use channels specified by national implementing legislation

**To affected individuals:**
- Only required when breach is **likely to adversely affect** the individual's rights and freedoms
- Higher threshold than GDPR: consider operational sensitivity, ongoing investigations
- May be **delayed or withheld** if notification would prejudice investigation or reveal intelligence sources

**To other competent authorities:**
- If breach affects data received from another LEA or partner, notify them immediately
- Include assessment of onward disclosure risk

**Example:** A law enforcement agency's Flowintel instance is compromised, exposing case files on an active investigation. The breach includes witness identities. Risk assessment: high (risk to witnesses' safety). Action: notify supervisory authority immediately; delay individual notification pending risk mitigation (witness protection measures); notify partner agencies whose data was affected.

## 2. Flowintel breach scenarios

### Scenario A: Unauthorised access to case data

**Impact:**
- Exposure of investigation details, intelligence sources, witness statements
- Potential compromise of ongoing operations
- Risk of onward disclosure to subjects of investigation

**Detection indicators:**
- Unusual login patterns in audit logs
- Access to cases outside user's organisation or role
- Bulk export activity
- Failed authentication attempts followed by successful login

**Immediate response:**
1. Disable compromised user accounts
2. Isolate affected cases
3. Review audit logs for full scope of access
4. Check for data export via API, connectors, or PDF generation
5. Assess whether accessed data has been disclosed onwards

**Example:** An analyst's credentials are phished. Audit logs show the attacker accessed 12 cases over 48 hours but did not export data. Action: password reset, review all accessed cases for sensitivity, notify DPO, assess notification threshold (likely no external notification if no exfiltration confirmed).

### Scenario B: Data exfiltration via API or connector

**Impact:**
- Bulk extraction of cases, tasks, attachments, or intelligence objects
- Potential loss of control over sensitive data
- Risk of republication or sale of intelligence

**Detection indicators:**
- High-volume API calls from single token
- Connector activity outside normal patterns
- Large downloads of attachments or exports
- API activity during non-business hours

**Immediate response:**
1. Revoke compromised API tokens
2. Disable affected connector instances
3. Query audit logs for full list of extracted records
4. Notify receiving systems if connector was compromised (e.g., MISP instance)
5. Assess whether exfiltrated data is publicly searchable or re-distributed

**Example:** An API token with excessive permissions is leaked on a public repository. Logs show 5,000 case records exported before detection. Action: revoke token immediately, audit all extracted cases, notify supervisory authority (high risk due to volume), assess individual notification based on sensitivity of cases, implement token rotation policy.

### Scenario C: Insider misuse

**Impact:**
- Unlawful access by authorised user (curiosity browsing, stalking, unauthorised intelligence gathering)
- Breach of confidentiality and trust
- Potential disciplinary or criminal liability

**Detection indicators:**
- Access to cases unrelated to user's duties
- Searches for specific individuals outside operational need
- Access patterns inconsistent with assigned tasks
- Repeated access to closed or archived cases

**Immediate response:**
1. Suspend user access pending investigation
2. Generate detailed audit trail of all accessed records
3. Interview user to establish intent and scope
4. Assess whether accessed data was disclosed to third parties
5. Initiate disciplinary process

**Example:** A police officer uses Flowintel to look up information about a neighbour involved in a case handled by another team. Audit logs show 8 unauthorised accesses over 2 months. Action: suspend officer, notify supervisory authority (deliberate unlawful processing), notify affected individual (serious impact on rights), potential criminal prosecution under data protection legislation.

### Scenario D: Third-party compromise (hosting provider or cloud infrastructure)

**Impact:**
- Infrastructure-level breach affecting multiple organisations or instances
- Potential access to database, backups, or encryption keys
- Risk of systemic compromise beyond single user or case

**Detection indicators:**
- Notification from hosting provider or cloud vendor
- Unexplained system behaviour (performance degradation, unauthorised configuration changes)
- Multiple user accounts compromised simultaneously
- Evidence of lateral movement or privilege escalation

**Immediate response:**
1. Coordinate with processor (hosting provider)
2. Request detailed incident report and timeline from processor
3. Assess scope using Flowintel audit logs (compare against processor's logs)
4. Determine which organisations/cases affected
5. Implement containment measures (isolate network segment, rotate credentials, restore from clean backup)
6. Notify all affected Controllers if multi-tenancy breach

**Example:** Cloud provider hosting Flowintel suffers database exposure due to misconfigured firewall. Provider notifies within 24 hours. Impact assessment shows read-only access to 3 organisations' data for 6 hours. Action: provider (as processor) notifies Controller within contractual SLA; Controller assesses notification threshold per organisation; implements additional network segmentation; reviews processor security controls.

## 3. Breach assessment workflow

### Step 1: Detect and contain (immediate – within 1 hour)
- Isolate affected systems or accounts
- Preserve evidence (take snapshots, export logs)
- Prevent further unauthorised access
- Notify incident response team and DPO

### Step 2: Assess scope (usually within 24 hours)
- Use Flowintel audit logs to identify:
  - Which cases/tasks were accessed or modified
  - Which users or API tokens involved
  - Time window of breach
  - Whether data was exported or exfiltrated
- Cross-reference with infrastructure logs (web server, database, network)

### Step 3: Classify severity

**Low risk:**
- Internal access by authorised user with legitimate need
- No special category or law enforcement data involved
- No exfiltration or onward disclosure
- Limited scope (single case, short duration)
- **Action:** Document in breach register; no external notification

**Medium risk:**
- Unauthorised access but limited scope
- Standard personal data (names, contact details) exposed
- No evidence of onward disclosure
- Controlled exposure within organisation or trusted partners
- **Action:** Notify DPO; assess notification threshold; may notify supervisory authority

**High risk:**
- Special category data exposed (health, biometric, criminal records)
- Large-scale breach (hundreds or thousands of records)
- Evidence of exfiltration or publication
- Witness, victim, or undercover officer identities compromised
- Cross-border disclosure without safeguards
- **Action:** Notify supervisory authority; likely individual notification required; coordinate with partner agencies

### Step 4: Notify (within 72 hours for GDPR; without undue delay for LE)

**Internal notifications (immediate):**
- DPO
- Senior management / incident response lead
- Information security team
- Legal counsel

**External notifications (as required):**
- Supervisory authority (use official channels)
- Affected individuals (if high risk)
- Partner organisations whose data was affected
- Processor (if breach originated from their systems)
- Other competent authorities

**Notification content must include:**
- Nature of the breach (what happened, when, how detected)
- Categories and approximate number of affected individuals
- Categories and approximate number of affected records
- Likely consequences of the breach
- Measures taken or proposed to address the breach
- Contact point for further information (typically DPO)

### Step 5: Document (usually within 72 hours)

Create a dedicated case record in Flowintel (or separate secure system) containing:
- Timeline: detection, containment, assessment, notification
- Scope: affected data, individuals, systems
- Root cause analysis
- Notification decisions and rationale (if withheld, document why)
- Evidence (audit logs, screenshots, correspondence)
- Actions taken and responsible parties

### Step 6: Remediate (usually within 30 days)

- Patch vulnerabilities or misconfigurations
- Implement additional technical controls (MFA, IP restrictions, enhanced logging)
- Update policies or procedures
- Retrain staff if human error involved
- Review access controls and permissions

### Step 7: Report to governance (usually within 60 days)

- Present post-incident review to senior management or data protection committee
- Document lessons learnt
- Update risk register
- Amend DPIA if processing activities change as result of breach

## 4. Documentation requirements

### Breach register (mandatory under GDPR Article 33(5))

The controller shall document any personal data breaches, comprising the facts relating to the personal data breach, its effects and the remedial action taken.

### Incident case file (recommended for high-severity breaches)

- Complete timeline with evidence
- Audit log extracts
- Communications (internal and external)
- Root cause analysis
- Remediation plan and status
- Post-incident review report
- Disciplinary or legal actions taken


## 6. Pre-Breach preparedness checklist

- [ ] Breach response procedure documented and approved
- [ ] Incident response team identified with defined roles
- [ ] DPO contact details available 24/7
- [ ] Supervisory authority contact details and notification process documented
- [ ] Audit logging enabled and regularly reviewed
- [ ] Access to audit logs secured 
- [ ] Backup and restore procedures tested
- [ ] Communication templates prepared (supervisory authority, individuals, partners)
- [ ] Annual breach response exercise conducted
- [ ] Staff trained on recognising and reporting potential breaches

---

## 7. Controller responsibilities

All breach response decisions—including scope assessment, notification determinations, and remediation—are made by the **Controller**, not the developer.

The developer (Flowintel maintainer) may provide:
- Technical support for audit log analysis
- Guidance on system behaviour or vulnerability assessment
- Software patches if breach exploited a code vulnerability

The developer **does not**:
- Access operational data
- Make notification decisions
- Determine legal obligations
- Interface with supervisory authorities on Controller's behalf

## Contact and escalation

- **DPO:** [Controller to insert]
- **Incident Response Lead:** [Controller to insert]
- **Supervisory Authority:** [Controller to insert – e.g., ICO, national DPA]
- **Flowintel Technical Support:** [Developer contact if contractual support exists]
