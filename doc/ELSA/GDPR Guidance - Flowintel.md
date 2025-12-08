# GDPR Guidance – Flowintel

*(Controller-focused, tooling-agnostic)*

## Purpose and framing

Flowintel provides case, task, note, attachment, and template management capabilities for operational security and investigative environments. Flowintel enables information handling but it **does not itself determine any lawful basis or processing purpose**.

Controllers operating Flowintel must ensure all processing meets GDPR requirements, including necessity, proportionality, accuracy, and limitation of use.

Flowintel does not act as a “Controller” or “Processor” under GDPR. It is simply a provided platform.

## Controller responsibility

Controllers are responsible for:

* deciding which categories of personal data are entered into Flowintel
* defining lawful basis (Art. 6; Art. 10 for offence data)
* setting retention limitations
* configuring role-based access
* determining data sharing and onward transfer rules
* ensuring their deployment complies with sector mandates (NIS, LEA, CSIRT, regulatory, etc.)

Once data leaves a given administrative boundary, **each recipient becomes controller for its own storage, use and onward disclosure.**

## Lawfulness

### General GDPR legal bases

Controllers may rely on:

| Lawful basis                             | Examples of use in Flowintel                                            |
| ---------------------------------------- | ----------------------------------------------------------------------- |
| **Art. 6(1)(e)** public task / authority | National CERT/CSIRT, regulatory breach reporting, incident coordination |
| **Art. 6(1)(c)** legal obligation        | NIS incident reporting, regulated breach handling                       |
| **Art. 6(1)(f)** legitimate interest     | Corporate SOC/IR where no authority mandate exists                      |
| **Art. 6(1)(a)** consent                 | Seldom suitable except voluntary reporter intake                        |

### Criminal offence data (Art. 10)

Flowintel use within policing / law enforcement falls under **Art. 10**. This requires a statutory mandate, internal classification plan, and specific retention authorisation.

## Purpose limitation

Flowintel must **not** be used to store or reuse data outside the originally communicated assignment:

* breach notifications must not be turned into unrelated profiling
* threat intelligence pivoting must not repurpose personal identifiers for HR decisions
* no forensic images should be retained longer than evidential need

Each entity is controller **only for the activity it defines**.

## Data minimisation

* do not upload complete disk dumps unless legally required
* redact personal identifiers when not needed to establish case context
* use object-structured metadata sparingly (tags, galaxy/labels, custom attributes)
* pseudonymisation is preferred but must not be mistaken for anonymisation.

## 6. Security measures for Flowintel

The deployment must configure:

| Control                              | Notes                               |
| ------------------------------------ | ----------------------------------- |
| RBAC with organisational scoping     | default per Flowintel design        |
| TLS and database-encryption at rest  | mandatory for sensitive deployments |
| Audit logging                        | implemented by platform     |
| Segregation between organisations    | enforced by Flowintel     |
| Soft-delete + administrative removal | supports layered retention disposal |

Flowintel provides the mechanism but the **correct configuration is a Controller duty.**

## Cross-border transfers

Controllers must:

* document any transfer beyond the originating jurisdiction
* verify adequacy and authorisations
* classify case data before transfer

No forwarding should occur without a classification and clearance model.

## Accuracy and correction

* all data added through cases/tasks must be reviewed periodically
* outdated indicators, expired credentials, and incorrect identifiers must be removed
* delegation/validation workflows must be used to track provenance

## Transparency

Controllers must:

* provide privacy notices
* document exceptions (e.g. LEA where disclosure undermines investigation)
* maintain internal classification logs and retention ledger

## Storage limitation

Controllers define:

* retention clock per case category
* exceptional extensions for litigation or public mandate
* archived vs active case separation

## Joint controllers

Where two or more agencies maintain a shared Flowintel deployment, a written arrangement must specify:

* disclosure triggers
* case access tiers
* retention duration per jurisdiction
* reporting rights and limitations

# Summary

Flowintel provides structured case and task management but **does not decide legality, retention, or scope of processing**.
GDPR compliance rests with each Controller operating an instance, including:

* lawful basis and mandate
* high-assurance access control
* sharing classification rules
* retention enforcement
* disclosure logging

Flowintel must be documented not as a sharing authority but as an enabling mechanism.
