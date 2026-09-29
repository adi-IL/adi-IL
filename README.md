<p align="left">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="assets/logo-light.png">
    <img src="assets/logo-light.png" alt="adityaai logo" width="72">
  </picture>
</p>

### Aditya Gaurav · AI Systems Architect

**Building the layer between research and production.**

I design production AI systems (agent harnesses, evaluation, sandboxing, and the plumbing between models and real workloads) and write about it at [adityaai.dev](https://www.adityaai.dev). I also ship fixes into the infrastructure AI runs on: TensorFlow kernels and XLA, gVisor's sandboxed kernel, and Grafana. Nearly all of them come with a regression test that upstream now runs.

> The model proposes. Deterministic arbiters dispose.

### Upstream ledger

Merged fixes in the projects AI infrastructure is built on, led by TensorFlow, gVisor, and Grafana. The list is generated daily from public GitHub data, and only reviewed entries appear.

<!-- BEGIN:ledger -->
<img src="assets/ledger.svg" alt="Upstream ledger summary" width="100%">

#### TensorFlow · 8 merged

**tensorflow/tensorflow [#125856](https://github.com/tensorflow/tensorflow/pull/125856)** · Sep 2026 · merged · `+22 −0`<br>
**Issue** LookupTableExport skipped the dtype signature check its sibling ops run, so a key or value dtype mismatch hit a CHECK and killed the process.<br>
**Fix** Call MatchSignature before exporting, so a mismatch returns InvalidArgumentError. [Test ↗](https://github.com/tensorflow/tensorflow/blob/c21d28ea07c47872d5e2efd29d0b3b046b6dbdaf/tensorflow/python/kernel_tests/data_structures/lookup_ops_test.py#L119)

**tensorflow/tensorflow [#127438](https://github.com/tensorflow/tensorflow/pull/127438)** · Sep 2026 · merged · `+33 −2`<br>
**Issue** TensorListScatter computed its resize length as a signed highest_index + 1, so an index of INT32_MAX overflowed before the resize.<br>
**Fix** Reject INT32_MAX with InvalidArgument and compute the length as size_t, matching the sibling IntoExistingList op. [Test ↗](https://github.com/tensorflow/tensorflow/blob/8a3a427ea8c7f04f04236801a115e974834c9bb6/tensorflow/python/kernel_tests/data_structures/list_ops_test.py#L612)

**tensorflow/tensorflow [#126688](https://github.com/tensorflow/tensorflow/pull/126688)** · Sep 2026 · merged · `+81 −11`<br>
**Issue** Grappler fused MatMul or Conv2D with a broadcast bias like [1, N], but the Eigen and GPU kernels demanded a 1-D bias, so the fused op failed inside tf.function.<br>
**Fix** Accept any bias whose leading dimensions are all 1, matching the remapper and the MKL kernel. [Test ↗](https://github.com/tensorflow/tensorflow/blob/908220bfa21522475b25b9de1ff4492f93fdbe0b/tensorflow/python/kernel_tests/math_ops/matmul_op_test.py#L63)

**tensorflow/tensorflow [#126937](https://github.com/tensorflow/tensorflow/pull/126937)** · Sep 2026 · merged · `+122 −107`<br>
**Issue** The GPU Dilation kernels counted elements in 32-bit signed ints, so tensors past INT32_MAX elements overflowed, tripped a CHECK, or launched too few threads.<br>
**Fix** Promote counts and loop indices to int64 and launch through GetGpuLaunchConfig64, as gather_nd already does.

**tensorflow/tensorflow [#126936](https://github.com/tensorflow/tensorflow/pull/126936)** · Sep 2026 · merged · `+74 −2`<br>
**Issue** An automated import in 2020 dropped the EuclideanNorm registration from tf2xla, so reduce_euclidean_norm failed to compile under jit_compile.<br>
**Fix** Restore the PreprocessInput hook on XlaReductionOp and register EuclideanNorm as square, sum, sqrt. [Test ↗](https://github.com/tensorflow/tensorflow/blob/5d2d6216761c6344c621a93d84ce67027f6723dd/tensorflow/compiler/tests/reduce_ops_test.py#L182)

**tensorflow/tensorflow [#126935](https://github.com/tensorflow/tensorflow/pull/126935)** · Sep 2026 · merged · `+29 −1`<br>
**Issue** tf2xla registered BesselI0e and BesselI1e but not BesselI0 and BesselI1, so bessel_i0 and bessel_i1 aborted XLA compilation.<br>
**Fix** Register both from existing primitives: I0(x) = I0e(x) * exp(|x|), and the same for I1. [Test ↗](https://github.com/tensorflow/tensorflow/blob/957c552af12162dbc096f2258c56c1081a733edc/tensorflow/compiler/tests/unary_ops_test.py#L218)

**tensorflow/tensorflow [#126449](https://github.com/tensorflow/tensorflow/pull/126449)** · Sep 2026 · merged · `+66 −25`<br>
**Issue** XLA RangeOp under jit_compile had no path for half, bfloat16, or integer dtypes, so those ranges failed at compile time.<br>
**Fix** Wire the missing dtype handlers so Range works under XLA for those types. [Test ↗](https://github.com/tensorflow/tensorflow/blob/b95e0be7f86632cec71f29ff379e98184481283b/tensorflow/compiler/tests/ternary_ops_test.py#L62)

**tensorflow/tensorflow [#125859](https://github.com/tensorflow/tensorflow/pull/125859)** · Aug 2026 · merged · `+22 −5`<br>
**Issue** A convolution with an invalid rank aborted the Python process instead of returning an error.<br>
**Fix** Raise ValueError so callers can catch the bad shape and keep the process alive. [Test ↗](https://github.com/tensorflow/tensorflow/blob/deb1655618e2469a5953448d3d22fe92a77c632e/tensorflow/python/kernel_tests/nn_ops/atrous_convolution_test.py#L275)

#### gVisor · 1 merged

**google/gvisor [#14505](https://github.com/google/gvisor/pull/14505)** · Sep 2026 · merged · `+33 −0`<br>
**Issue** Positional reads and writes on pseudo-terminals returned EINVAL in gVisor, where Linux returns ESPIPE.<br>
**Fix** Set DenyPRead and DenyPWrite on both devpts file descriptions so pread and pwrite return ESPIPE. [Test ↗](https://github.com/google/gvisor/blob/d327f2d30b04e5ba65b57d55b12b180130cac254/test/syscalls/linux/pty.cc#L2908)

#### Grafana · 1 merged

**grafana/grafana [#131335](https://github.com/grafana/grafana/pull/131335)** · Aug 2026 · merged by @gelicia · `+64 −10`<br>
**Issue** Value-mapping range inputs rejected minus signs, so you could not set a negative lower or upper bound.<br>
**Fix** Accept signed numbers in the range fields so negative bounds type normally. [Test ↗](https://github.com/grafana/grafana/blob/8d215375a0ea5ded82ec3266254a4f39aad64b5d/public/app/features/dimensions/editors/ValueMappingsEditor/ValueMappingsEditorModal.test.tsx#L159)

<details>
<summary>8 more merged fixes</summary>

**e2b-dev/herdr-e2b-sandbox [#36](https://github.com/e2b-dev/herdr-e2b-sandbox/pull/36)** · Sep 2026 · merged by @OndrejDrapalik · `+225 −26`<br>
**Issue** One unreadable remote file or failed local write aborted the whole pull batch.<br>
**Fix** Handle failures per file, finish the remaining batches, and exit 1 on an incomplete pull. [Test ↗](https://github.com/e2b-dev/herdr-e2b-sandbox/blob/6cc81c43afec6f11b6e5a30788f5d28307054eb8/test/download-cli.test.js#L77)

**e2b-dev/herdr-e2b-sandbox [#35](https://github.com/e2b-dev/herdr-e2b-sandbox/pull/35)** · Sep 2026 · merged by @OndrejDrapalik · `+51 −6`<br>
**Issue** Missing, nonpositive, or nonfinite pane sizes could reach PTY creation as invalid geometry.<br>
**Fix** Route creation, resizing, and the attach plan through one helper that clamps to positive integers. [Test ↗](https://github.com/e2b-dev/herdr-e2b-sandbox/blob/de09335ce9dd336e5bd4fae29d075d4e9aba2032/test/attach-plan.test.js#L88)

**e2b-dev/herdr-e2b-sandbox [#34](https://github.com/e2b-dev/herdr-e2b-sandbox/pull/34)** · Sep 2026 · merged by @OndrejDrapalik · `+97 −8`<br>
**Issue** Malformed input or a setup failure crashed exec.js before it emitted its JSON result.<br>
**Fix** Validate inputs and route parse and config errors through the existing result emitter. [Test ↗](https://github.com/e2b-dev/herdr-e2b-sandbox/blob/11943a4a49855759a34540290cca4e88bb57bf78/test/exec.test.js#L39)

**e2b-dev/herdr-e2b-sandbox [#33](https://github.com/e2b-dev/herdr-e2b-sandbox/pull/33)** · Sep 2026 · merged by @OndrejDrapalik · `+37 −3`<br>
**Issue** Concurrent writes in one process shared a temp path, causing overwrites and rename failures.<br>
**Fix** Give each write its own temp file and clean it up on failure. [Test ↗](https://github.com/e2b-dev/herdr-e2b-sandbox/blob/f5f5b6abeabad87e846f4820e6b2945b448e615a/test/store.test.js#L13)

**e2b-dev/herdr-e2b-sandbox [#21](https://github.com/e2b-dev/herdr-e2b-sandbox/pull/21)** · Aug 2026 · merged by @OndrejDrapalik · `+14 −3`<br>
**Issue** Under the daemon, inherited credentials skipped the resolver, so config changes needed a restart.<br>
**Fix** Always run the resolver under the daemon. [Test ↗](https://github.com/e2b-dev/herdr-e2b-sandbox/blob/1e9da2a0bb017cb7d54eb0cdc4c168650c0abf56/test/cli.test.sh#L652)

**GoogleCloudPlatform/dataflow-solution-guides [#224](https://github.com/GoogleCloudPlatform/dataflow-solution-guides/pull/224)** · Aug 2026 · merged by @iht · `+233 −22`<br>
**Issue** The CDP pipeline read its BigQuery schema from a relative path at import time, which failed on Dataflow workers.<br>
**Fix** Load the schema through a runtime option and type the coupon join. [Test ↗](https://github.com/GoogleCloudPlatform/dataflow-solution-guides/blob/73f05d16ab6050325ec493a1fd40d3b6a459df57/pipelines/cdp/tests/test_customer_data_platform.py#L83)

**google/mug [#130](https://github.com/google/mug/pull/130)** · Aug 2026 · merged by @fluentfuture · `+94 −4`<br>
**Issue** Regex escape handling swallowed malformed input, and the error suite never ran because the files were named *Tests.java instead of *Test.java.<br>
**Fix** Fail on bad escapes, and rename the suite so Surefire actually executes it. [Test ↗](https://github.com/google/mug/blob/e34619eecd3eade471f59fbf9d91647767c0557c/dot-parse/src/test/java/com/google/common/labs/regex/RegexParserErrorTest.java#L792)

**pvlib/pvlib-python [#2821](https://github.com/pvlib/pvlib-python/pull/2821)** · Aug 2026 · merged by @kandersolar · `+22 −8`<br>
**Issue** delta_kt_prime halved the difference when only one neighbor was valid.<br>
**Fix** Use the single valid neighbor difference as is. [Test ↗](https://github.com/pvlib/pvlib-python/blob/482ca3c6fee3aeb357166505c02d2d9fc92fe6e2/tests/test_irradiance.py#L798)

</details>
<!-- END:ledger -->

### Proof gallery

A fix without a test is a claim. Each link below opens the regression test in the upstream tree, at the exact commit where it landed.

<!-- BEGIN:proofs -->
| Project | Fix | Regression test, at the commit that landed |
|---|---|---|
| TensorFlow | [#125856](https://github.com/tensorflow/tensorflow/pull/125856) fix: validate output signatures in LookupTableExportOp to prevent crash on dtype mismatch | [`testExportSignatureMismatch`](https://github.com/tensorflow/tensorflow/blob/c21d28ea07c47872d5e2efd29d0b3b046b6dbdaf/tensorflow/python/kernel_tests/data_structures/lookup_ops_test.py#L119) |
| TensorFlow | [#127438](https://github.com/tensorflow/tensorflow/pull/127438) fix(kernels): reject INT32_MAX index in TensorListScatter resize | [`testScatterRejectsUnrepresentableLength`](https://github.com/tensorflow/tensorflow/blob/8a3a427ea8c7f04f04236801a115e974834c9bb6/tensorflow/python/kernel_tests/data_structures/list_ops_test.py#L612) |
| TensorFlow | [#126688](https://github.com/tensorflow/tensorflow/pull/126688) [FusedOps] Support broadcast-shaped bias with leading 1s in fused MatMul and Conv2D | [`testMatMulAddBroadcastInTfFunction`](https://github.com/tensorflow/tensorflow/blob/908220bfa21522475b25b9de1ff4492f93fdbe0b/tensorflow/python/kernel_tests/math_ops/matmul_op_test.py#L63) |
| TensorFlow | [#126936](https://github.com/tensorflow/tensorflow/pull/126936) fix(tf2xla): register EuclideanNorm reduction OpKernel | [`testReduceEuclideanNorm`](https://github.com/tensorflow/tensorflow/blob/5d2d6216761c6344c621a93d84ce67027f6723dd/tensorflow/compiler/tests/reduce_ops_test.py#L182) |
| TensorFlow | [#126935](https://github.com/tensorflow/tensorflow/pull/126935) fix(tf2xla): register XLA OpKernels for BesselI0 and BesselI1 | [`testBesselI0 / testBesselI1`](https://github.com/tensorflow/tensorflow/blob/957c552af12162dbc096f2258c56c1081a733edc/tensorflow/compiler/tests/unary_ops_test.py#L218) |
| TensorFlow | [#126449](https://github.com/tensorflow/tensorflow/pull/126449) [XLA:tf2xla] Support half, bfloat16, and integer dtypes in RangeOp | [`testRange`](https://github.com/tensorflow/tensorflow/blob/b95e0be7f86632cec71f29ff379e98184481283b/tensorflow/compiler/tests/ternary_ops_test.py#L62) |
| TensorFlow | [#125859](https://github.com/tensorflow/tensorflow/pull/125859) fix: validate minimum input rank in convolution_internal to prevent crash on invalid shapes | [`testInvalidInputRank`](https://github.com/tensorflow/tensorflow/blob/deb1655618e2469a5953448d3d22fe92a77c632e/tensorflow/python/kernel_tests/nn_ops/atrous_convolution_test.py#L275) |
| gVisor | [#14505](https://github.com/google/gvisor/pull/14505) devpts: return ESPIPE on positional read and write | [`PtyTest.PositionalIO`](https://github.com/google/gvisor/blob/d327f2d30b04e5ba65b57d55b12b180130cac254/test/syscalls/linux/pty.cc#L2908) |
| Grafana | [#131335](https://github.com/grafana/grafana/pull/131335) ValueMappings: Allow editing negative bounds in range mappings | [`should allow editing negative bounds on existing range mapping`](https://github.com/grafana/grafana/blob/8d215375a0ea5ded82ec3266254a4f39aad64b5d/public/app/features/dimensions/editors/ValueMappingsEditor/ValueMappingsEditorModal.test.tsx#L159) |
<!-- END:proofs -->

### Lab

- **[MidSphere](https://github.com/adi-IL/MidSphere)**: an autonomous context circuit-breaker for data platforms. [Live demo](https://midsphere.vercel.app).
- **[Essays](https://www.adityaai.dev/articles)**: a short shelf on agent harnesses, verification, sandboxing, and inference economics.

### Notes

Latest essays from [adityaai.dev](https://www.adityaai.dev/articles):

<!-- BEGIN:notes -->
- [Shared caches beat sandbox walls](https://www.adityaai.dev/articles/shared-caches-beat-sandbox-walls) · Sep 2026
- [The Verification Gap: Why Reasoning Models Need Deterministic Arbiters](https://www.adityaai.dev/articles/the-verification-gap) · Sep 2026
- [The Chat Template Trap: Why Dynamic Agent State Crashes Open-Weight Models](https://www.adityaai.dev/articles/the-chat-template-trap) · Sep 2026
- [The Invariant Problem in Autonomous Remediation: Why Code Synthesis Fails Without Closed-Loop Verification](https://www.adityaai.dev/articles/closed-loop-remediation-architecture) · Aug 2026
- [Sandboxing Architectures for Autonomous Agents: MicroVMs, gVisor, and the Egress Dilemma](https://www.adityaai.dev/articles/sandboxing-architectures-for-agents) · Aug 2026
<!-- END:notes -->

### Links

[adityaai.dev](https://www.adityaai.dev) · [LinkedIn](https://www.linkedin.com/in/adityaai/) · [X @adityaaidev](https://x.com/adityaaidev) · [aiexpert@adityaai.dev](mailto:aiexpert@adityaai.dev) · [Certifications](https://www.credly.com/users/aditya-gaurav.12219822/badges)

<sub>adityaai · lab</sub>
