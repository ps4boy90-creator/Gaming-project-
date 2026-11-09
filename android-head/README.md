# Android Head — wired like a human

A life-size android head built procedurally in three.js. It is a machine: camera eyes on
gimbal balls, ribbed actuators with tendon cables, cable harnesses with plugs, coolant
hoses with clamps and finned processor modules behind a ceramic face plate. Every
component is mounted where the human part it replaces sits and plugs into the same
neighbours, so the wiring follows real anatomy.

- **Interactive viewer:** [`index.html`](index.html) — one self-contained file, no build step
- **Game asset:** [`android-head.glb`](android-head.glb) — binary glTF, metres, 65 parts as 331 named meshes
- **Exporter:** [`tools/export-glb.js`](tools/export-glb.js) — regenerates the GLB from the viewer

## What is modelled

65 parts in seven systems. Each is an android component that stands in for a named human structure.

| Android system | Stands in for | Human structures covered |
| --- | --- | --- |
| Chassis | Skeleton | Cranial shell in three panels (dome, face plate, jaw), mandible on a hinge at the temporomandibular joint, cheek struts, teeth, atlas, axis, C3–C7, discs, hyoid |
| Compute core | Brain & spinal cord | Four lobes per hemisphere, cerebellum, thalamus with its visual and auditory relay nuclei, corpus callosum, midbrain, pons, medulla, spinal cord, six mapped cortical areas |
| Sensors | Sense organs | Eyes, outer ear and canal, eardrum and ossicles, cochlea, semicircular canals, olfactory epithelium and bulb, tongue |
| Wiring harness | Nerves & tracts | Cranial nerves I, II, III/IV/VI, V (three divisions), VII (five branches), VIII, X, XI, XII, plus the optic radiation, central auditory pathway, trigeminothalamic tract, corticobulbar tract and medial longitudinal fasciculus |
| Actuators | Muscles | Six extraocular muscles per eye with the trochlea pulley, masseter, temporalis, digastric, sternocleidomastoid, zygomaticus major, orbicularis oris |
| Coolant & power loop | Blood supply | Common, internal and external carotids, facial and temporal arteries, vertebral and basilar arteries, circle of Willis, three cerebral arteries per side, dural sinuses, internal jugular veins |
| Voice unit | Airway & voice | Larynx with vocal folds, trachea |

Connections follow the real routes. A few examples:

- The optic nerve is drawn as two fibre groups per eye. The nasal group crosses at the
  chiasm and the temporal group stays on its side, so each optic tract carries one half
  of the visual field from both eyes to the lateral geniculate nucleus, then to V1.
- The vertebral arteries climb through the transverse foramina of the neck vertebrae,
  loop around the atlas and merge into the basilar artery. With the two internal
  carotids they feed the circle of Willis, which sits around the optic chiasm.
- The facial nerve runs past the inner ear, exits behind the jaw and splits into its
  five branches over the masseter.
- Actuators and cables attached to the jaw are rebuilt as it rotates, so the units
  standing in for the masseter, temporalis and digastric lengthen and shorten with it.

## Using the viewer

Open `index.html` in a browser (it loads three.js r128 from cdnjs).

- Drag to orbit, scroll or pinch to zoom, shift-drag to pan.
- Tap a part to isolate it together with everything it plugs into. The panel names the
  android component, the human structure it stands in for and how the original works.
- **Shell** switches the cranial shell between glass, a sagittal cutaway, solid and hidden.
- **Jaw** opens the mandible.
- **Signal paths** plays seven routes relay by relay: sight, hearing, the balance reflex
  (the head turns and the eyes counter-rotate), speech (the jaw moves), smell, face touch
  and blood flow.

## Using the GLB

`android-head.glb` is exported with the shell solid and the jaw closed. The scene is in
metres, Y up, face toward +Z, with the origin at ear level in the middle of the head.

Meshes are named `<system>.<part>[.NN]`, for example `nerves.cn2.00` or
`actuators.masseter.01`, so a system or a part can be shown, hidden or re-materialed by
name. The shell is `chassis.shell.00` (dome and face), `chassis.shell.01` (neck sleeve)
and the jaw panel is one of the `chassis.jaw.*` meshes. Hide those to see inside.

The jaw hinge axis runs along X through (0, −0.009, 0.001) m. The jaw meshes are children
of a node positioned on that axis, so rotating that node about X opens the mouth. The
actuators are static in the GLB; only the viewer rebuilds them live. The cooling slots
in the processor housings are cut in a shader in the viewer, so in the GLB the housings
are plain metal shells over the glowing blocks. Cable, actuator and hose colours are
stored as vertex colours.

To regenerate after editing the model:

```bash
cd android-head
npm i --no-save three@0.128.0 playwright
node tools/export-glb.js
```

## Accuracy notes

- Positions, proportions and routes are modelled from standard anatomy at life size
  (head 15.2 cm wide, 23 cm crown to chin), then built as machine parts. It is a
  teaching and game model, not a clinical one and not an engineering design.
- The glossopharyngeal nerve (IX) is not drawn separately; it travels with the vagus.
  The recurrent laryngeal branch of the vagus loops below the model, so only the
  superior laryngeal branch is shown.
- The oesophagus, pharynx, salivary glands and most of the smaller facial muscles are
  left out to keep the wiring readable.
