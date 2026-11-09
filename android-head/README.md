# Android Head — wired like a human

A life-size android head built procedurally in three.js. Every component sits where the
human original sits and connects to the same neighbours, so the model works as an
anatomy reference and as a game asset.

- **Interactive viewer:** [`index.html`](index.html) — one self-contained file, no build step
- **Game asset:** [`android-head.glb`](android-head.glb) — binary glTF, metres, 65 parts as 315 named meshes
- **Exporter:** [`tools/export-glb.js`](tools/export-glb.js) — regenerates the GLB from the viewer

## What is modelled

65 parts in seven systems. Each has a human name and an android equivalent.

| System (human) | Android build | Parts |
| --- | --- | --- |
| Skeleton | Chassis | Cranial shell in three panels (dome, face plate, jaw), mandible on a hinge at the temporomandibular joint, cheek struts, teeth, atlas, axis, C3–C7, discs, hyoid |
| Brain & spinal cord | Compute core | Four lobes per hemisphere, cerebellum, thalamus with its visual and auditory relay nuclei, corpus callosum, midbrain, pons, medulla, spinal cord, six mapped cortical areas |
| Sense organs | Sensors | Eyes, outer ear and canal, eardrum and ossicles, cochlea, semicircular canals, olfactory epithelium and bulb, tongue |
| Nerves & tracts | Wiring harness | Cranial nerves I, II, III/IV/VI, V (three divisions), VII (five branches), VIII, X, XI, XII, plus the optic radiation, central auditory pathway, trigeminothalamic tract, corticobulbar tract and medial longitudinal fasciculus |
| Muscles | Actuators | Six extraocular muscles per eye with the trochlea pulley, masseter, temporalis, digastric, sternocleidomastoid, zygomaticus major, orbicularis oris |
| Blood supply | Coolant & power loop | Common, internal and external carotids, facial and temporal arteries, vertebral and basilar arteries, circle of Willis, three cerebral arteries per side, dural sinuses, internal jugular veins |
| Airway & voice | Voice unit | Larynx with vocal folds, trachea |

Connections follow the real routes. A few examples:

- The optic nerve is drawn as two fibre groups per eye. The nasal group crosses at the
  chiasm and the temporal group stays on its side, so each optic tract carries one half
  of the visual field from both eyes to the lateral geniculate nucleus, then to V1.
- The vertebral arteries climb through the transverse foramina of the neck vertebrae,
  loop around the atlas and merge into the basilar artery. With the two internal
  carotids they feed the circle of Willis, which sits around the optic chiasm.
- The facial nerve runs past the inner ear, exits behind the jaw and splits into its
  five branches over the masseter.
- Muscles and nerves attached to the mandible are rebuilt as the jaw rotates, so the
  masseter, temporalis and digastric lengthen and shorten with it.

## Using the viewer

Open `index.html` in a browser (it loads three.js r128 from cdnjs).

- Drag to orbit, scroll or pinch to zoom, shift-drag to pan.
- Tap a part to isolate it together with everything it connects to. The panel gives the
  human name, the android build and what it does.
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
muscles are static in the GLB; only the viewer rebuilds them live.

To regenerate after editing the model:

```bash
cd android-head
npm i --no-save three@0.128.0 playwright
node tools/export-glb.js
```

## Accuracy notes

- Positions and proportions are modelled from standard anatomy at life size (head
  15.2 cm wide, 23 cm crown to chin). Structures are simplified into tubes, lofted
  surfaces and ellipsoids. It is a teaching and game model, not a clinical one.
- The glossopharyngeal nerve (IX) is not drawn separately; it travels with the vagus.
  The recurrent laryngeal branch of the vagus loops below the model, so only the
  superior laryngeal branch is shown.
- The oesophagus, pharynx, salivary glands and most of the smaller facial muscles are
  left out to keep the wiring readable.
