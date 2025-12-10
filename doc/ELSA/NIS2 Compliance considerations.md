# NIS2 Compliance considerations for Flowintel

## Scope and positioning

Flowintel is a platform used to manage:

* cases and incident records,
* tasks and operational workflows,
* supporting documentation and evidence,
* operational intelligence and correlation,
* optional integrations

Flowintel is **not an operator** under NIS2. It is **provided as software** and becomes subject to NIS2 obligations only when installed and operated by an entity falling under the Directive.

Once deployed, **the Controller operating Flowintel** is responsible for incident notification, risk management, and security measures.

## Relevant NIS2 provisions

### Risk management measures

(NIS2, Art. 21)

The Controller must ensure the Flowintel deployment includes:

* access control and role segmentation
* secure software configuration
* logging and monitoring of activities
* encryption in transit and at rest
* business continuity and backup routines
* vulnerability disclosure policy

Flowintel supports these with:

* role-based access per organisation
* audit logging of user actions
* configurable TLS
* isolated organisational data scopes
* approvals

### Reporting requirements

(NIS2, Art. 23–24)

If Flowintel is used for security incident handling, the Controller must:

* establish detection procedures
* classify incidents per NIS2 thresholds
* notify competent authority/CSIRT "without undue delay"

Flowintel facilitates incident case tracking but **does not send notifications automatically**. Notification obligations rest with the Controller.

### Supply chain expectations

(NIS2, Art. 21(2)(d))

Flowintel qualifies as **software supply chain** component. 

The developer provides:

* code updates
* release notes
* security advisories

The Controller must:

* assess software updates,
* implement timely patching,
* maintain documented deployment hardening.

## Information sharing expectations

Flowintel may be used to:

* share case elements,
* request assistance between CSIRTs or competent bodies,
* exchange templates, taxonomies, tags.

Sharing rules must follow:

* national NIS2 transposition,
* internal classification schemes,
* confidentiality markings.

Flowintel provides structural support (tags, visibility, organisational boundaries) but does not determine:

* what is shared,
* level of classification,
* exchange partners.

## Classification and handling

The Controller must define:

* internal classification scheme,
* authorised disclosure levels,
* storage and export restrictions.

Flowintel supports configurable tagging on:

* case sensitivity
* disclosure level
* operational status
* priority / criticality

Tags **do not replace binding legal markings**; they only provide structure.

## Logging, audit, and forensics

Under NIS2, operational visibility and investigation traceability are essential.

Flowintel provides:

* audit trails of user actions,
* record of case/task modifications,
* timestamped attribution.

The Controller must:

* retain logs per national retention rules,
* protect audit trail integrity,
* include logs in post-incident reporting.

## Integration and cross-border flows

If Flowintel integrates with other exchange platforms controller obligations apply:

* define legal basis for transfer,
* ensure cooperation agreements exist,
* apply access restriction and filtering.

Flowintel does **not** synchronise upstream without administrative intent: all data flows are initiated and configured by the Controller.

## Security governance responsibilities

| Responsibility                 | Developer | Controller |
| ------------------------------ | --------- | ---------- |
| Secure development             | Yes       | No         |
| Hosting, storage, backup       | No        | Yes        |
| Legal basis for processing     | No        | Yes        |
| Classification policy          | No        | Yes        |
| Incident notification to CSIRT | No        | Yes        |
| Retention & deletion rules     | No        | Yes        |
| Access control assignment      | No        | Yes        |

## Conclusion

Flowintel, as a platform, aligns structurally with NIS2 expectations for:

* incident documentation,
* secure information handling,
* cross-entity cooperation where authorised.

However, compliance obligations sit with the **operating Controller**, who must:

* define handling rules,
* implement security controls,
* execute reporting duties,
* manage retention and classification.

The developer does not access, host, or process operational data.

