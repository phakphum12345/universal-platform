# 3D Assembly Intelligence and Kinematics

**Status:** PROPOSED

## 1. Purpose

Represent multi-part assemblies, constraints, joints and motion so static and moving systems can be designed and analyzed before physical construction.

## 2. Assembly model

Part identity and revision; occurrence/instance; parent-child structure; coordinate frame; mating interfaces; fasteners; joint type; constraints; mass properties; material; tolerance; and source provenance.

## 3. Joint and motion concepts

Fixed, revolute, prismatic, cylindrical, spherical, planar and other supported joints. Each joint declares degrees of freedom, axis/plane, limits, friction assumptions and reference geometry. Motion inputs may include displacement, velocity, acceleration, torque or force profiles.

## 4. Kinematics

Calculate position, orientation, velocity, acceleration, reachable workspace, motion envelope and transmission relationships. For mechanisms, identify singularities, over-centre conditions and constraint conflicts where supported.

## 5. Assembly verification

Check missing constraints, over-constrained systems, degrees of freedom, interference, clearance, fastener access, service access, cable/hose routing and tolerance stack-up. Distinguish nominal geometry checks from tolerance-aware analysis.

## 6. Dynamic coupling

Where validated, connect mass/inertia and joint models to force, torque, vibration, damping and energy analysis through UEIC. Declare whether flexible-body effects, friction, backlash and impact are omitted.

## 7. Acceptance criteria

- [ ] Assembly hierarchy and part revisions are traceable.
- [ ] Joint definitions and degrees of freedom are explicit.
- [ ] Motion limits and envelopes are computed or marked unsupported.
- [ ] Collision and clearance results identify model versions.
- [ ] Tolerance assumptions are explicit.
- [ ] Unsupported dynamics are not represented as validated.
