# DPIA Screening – Flowintel (Controller)

## Context of processing

* **System:** Flowintel (case, task, intelligence, incident-handling platform)
* **Controller:** *[Deploying organisation]*
* **Processor(s):** *[Hosting provider / IT operations if subcontracted]*
* **System author:** Flowintel maintainer (no access to operational data)

### Purpose of processing

* Management of cases, investigations, incidents, and operational tasks
* Storage and correlation of intelligence, observables, reports, attachments
* Workflow handling (assign, review, approve, complete)
* Evidence documentation and traceability
* Optional ingest from external systems (e.g. MISP, threat feeds)

### Data subjects

To be specified by the Controller based on deployment context:

* Staff and users of the Controller
* Persons involved in investigations or case material
* External reporting entities or contributors
* Persons indirectly referenced in collected intelligence

## Nature of processing

* Creation and management of operational case records
* Storage of linked tasks, notes, attachments, indicators, and context
* Role-based access to compartmentalised case data
* Optional interconnection with intelligence exchange environments
* Long- and short-term archival depending on internal retention policy

**All processing decisions are determined by the Controller.**

## Types of personal data processed

To be completed by the Controller based on their usage:

* Identification data (names, emails, titles, organisational roles)
* Operational context data (accused persons, victims, witnesses, threat actors, contact points)
* Digital identifiers (IP addresses, domains, user handles, device IDs)
* Evidence attachments (images, logs, documents, forensic output)
* Access logs and audit trails
* Attachments (images, logs, documents, forensic outputs)
* Intelligence objects (MISP or equivalent structured objects)

## DPIA trigger questions

| Screening question                                | Yes/No  | Notes                                                                  |
| ------------------------------------------------- | ------- | ------------------- |
| Processing involves vulnerable data subjects?     |  | *LEA:* Almost always "Yes" due to victims/witnesses  |
| Large-scale monitoring or profiling?              |  | *Example:* Processing >10,000 individuals' data, or systematic surveillance |
| Data from law enforcement sources used?           |  | *LEA:* "Yes" if ingesting from police databases or intelligence agencies |
| Automated decision-making affecting individuals?  |  | *Example:* Automated case assignment based on profiling |
| Cross-border transfers (EU → outside)?            |  | *Include:* Cloud hosting in third countries, sharing with non-EEA LEAs |
| Processing of special categories (Art. 9)         |  | *Example:* Health data, biometric data, racial/ethnic origin |
| Processing of criminal offence data (Art. 10)     |  | *LEA:* Almost always "Yes" |
| Use of new or untested technology?                |  | *Example:* First deployment of Flowintel in your organisation |
| Aggregation of multiple datasets?                 |  | *Example:* Combining MISP feeds, police databases, open-source intelligence |
| Data retention beyond operational need?           |  | *Example:* Indefinite retention without deletion policy |
| Reuse of intelligence beyond original purpose?    |  | *Example:* Data collected for Incident A used in Investigation B without legal basis |
| Re-identification risk from technical indicators? |  | *Example:* IP addresses or device IDs linked to identifiable individuals |
| Lack of direct visibility by data subjects?       |  | *LEA:* Often "Yes" due to investigation confidentiality |

## Controller assessment and conclusion

* Screening **result**:
  * **☐ Full DPIA Required** (one or more "Yes" answers)  
  * **☐ DPIA Not Required** (all "No" answers – rare for Flowintel deployments)
* Rationale:
  * [Controller to document:]*
  * Why processing is necessary and proportionate
  * How risks to individuals' rights and freedoms have been assessed
  * Whether less intrusive alternatives were considered
* **Legal basis** (to be defined by the Controller):

## Risk areas (for Controller evaluation)

When conducting the full DPIA, assess these specific risks:

* Exposure of intelligence to unauthorised recipients
* Disproportionate data collection beyond investigative need
* Cross-border distribution without safeguards
* Retention without legal justification
* Insufficient audit oversight
* Use of personal identifiers in shared view panels without minimisation
* Importing external intelligence without classification alignment

**Operational risks**

* Insider misuse (unauthorised access to unrelated cases)
* Inadequate segregation between organisations or teams
* Weak access controls or password policies
* Inadequate training (users unaware of data protection obligations)

**Third-party risks**

* Processor (hosting provider) does not meet security standards
* Data shared with partners without Data Sharing Agreements
* * Sub-processors not vetted or documented

## Mitigations and safeguards

| Control                                        | Mandatory/Optional            | Notes                            |
| ---------------------------------------------- | ----------------------------- | -------------------------------- |
| Role-based access and least privilege          | Mandatory                     | Must align with internal policy  |
| Per-organisation data segregation              | Mandatory for LEA deployments | Prevents cross-team leakage      |
| Full audit logging of access and modifications | Mandatory                     | Controller must review logs      |
| Encryption in transit and at rest              | Mandatory                     | To be verified by hosting entity |
| Data minimisation at point of entry            | Mandatory                     | Classification controls required |
| Controlled sharing templates                   | Optional but recommended      | Avoid oversharing of identifiers |
| Formal retention & deletion schedule           | Mandatory                     | Must be documented before go-live |
| Secure external connector governance           | Mandatory when enabled        | Document feeds     |
| Breach response procedure                      | Mandatory              | Must be tested and staff trained            |
| Data Processing Agreement (DPA) with processor | Mandatory if using processor | Must comply with Article 28 GDPR  |

## Deployment responsibilities

| Responsibility                        | Developer | Controller          |
| ------------------------------------- | --------- | ------------------- |
| Hosting                               | ❌         | ✔️                  |
| Operational data access               | ❌         | ✔️                  |
| DPIA completion                       | ❌         | ✔️                  |
| Retention & deletion policies         | ❌         | ✔️                  |
| Role definition & access provisioning | ❌         | ✔️                  |
| Data sharing agreements               | ❌         | ✔️                  |
| Security patching of infrastructure   | ❌         | ✔️                  |
| Software updates                      | ✔️        | ✔️ (implementation) |

Governance, processing rules, legal basis, and retention are defined, operated, and enforced by the Controller.

## Next steps for controller

* [ ] Conduct full DPIA if screening indicates high risk
* [ ] Consult DPO and document advice
* [ ] Define lawful basis for intelligence and operational data processing
* [ ] Establish cross-agency sharing agreements where applicable
* [ ] Implement retention and deletion rules before first production use
* [ ] Validate hosting and access controls through security assessment
* [ ] Confirm audit review schedule (recommendation: quarterly)
* [ ] Document DPIA outcomes and maintain for review
* [ ] Review DPIA annually or when processing activities change significantly
