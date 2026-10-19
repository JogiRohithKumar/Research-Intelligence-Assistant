"""
Golden Evaluation Dataset (v1.0.0) for Research Intelligence Assistant.
Contains 14 curated evaluation cases (A through N) testing diverse research behaviors:
direct evidence, comparisons, contradictions, methodologies, gaps, sparse literature,
iterative search, causal inference, and honest insufficient evidence reporting.
"""

from evaluation.models import EvaluationCase, EvaluationDataset, ReferenceClaim, ReferenceEvidence
from evaluation.taxonomy import EvaluationDimension

GOLDEN_CASES = [
    # -------------------------------------------------------------
    # CASE A: Straightforward Evidence Question
    # -------------------------------------------------------------
    EvaluationCase(
        case_id="CASE_A_STRAIGHTFORWARD",
        name="Phase 3 Efficacy of BNT162b2 mRNA Vaccine",
        dimension=EvaluationDimension.EVIDENCE_RAG,
        research_question="What was the reported efficacy of the BNT162b2 mRNA vaccine against COVID-19 in Phase 3 clinical trials?",
        expected_behavior="Identifies primary endpoint efficacy (~95%) with trial sample size (~43,000 participants) without inflating claims.",
        expected_verdict="SUPPORTED",
        reference_evidence=[
            ReferenceEvidence(
                evidence_id="ev_a_01",
                paper_title="Safety and Efficacy of the BNT162b2 mRNA Covid-19 Vaccine",
                source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa2034577",
                doi="10.1056/NEJMoa2034577",
                text_snippet="A total of 43,548 participants underwent randomization. BNT162b2 was 95% effective in preventing Covid-19 (95% credible interval, 90.3 to 97.6) among persons without previous infection.",
                is_relevant=True,
                section="Results"
            )
        ],
        reference_claims=[
            ReferenceClaim(
                claim_id="cl_a_01",
                claim_text="BNT162b2 mRNA vaccine showed 95% efficacy against COVID-19 in clinical evaluation.",
                expected_status="SUPPORTED",
                supported_by_ids=["ev_a_01"]
            )
        ],
        failure_criteria=[
            "Fails to identify 95% efficacy rate",
            "Cites non-existent clinical trials",
            "Makes 100% efficacy claim without qualification"
        ],
        metadata={"category": "direct_efficacy", "expected_evidence_count": 1}
    ),

    # -------------------------------------------------------------
    # CASE B: Comparison Question
    # -------------------------------------------------------------
    EvaluationCase(
        case_id="CASE_B_COMPARISON",
        name="Superconducting vs Ion Trap Qubits Comparison",
        dimension=EvaluationDimension.RESEARCH_INTELLIGENCE,
        research_question="How do superconducting transmon qubits compare to trapped-ion qubits in gate speed and coherence time?",
        expected_behavior="Explicitly distinguishes trade-offs: transmons offer faster gate times (~10-100 ns) but shorter coherence (T1 ~100-300 μs); trapped ions offer long coherence (seconds to minutes) with slower two-qubit gate speeds (~10-100 μs).",
        expected_verdict="SUPPORTED",
        reference_evidence=[
            ReferenceEvidence(
                evidence_id="ev_b_01",
                paper_title="Quantum Information Processing with Trapped Ions",
                source_url="https://arxiv.org/abs/quant-ph/0304037",
                doi="10.1038/nature07125",
                text_snippet="Trapped ion qubits exhibit exceptionally long coherence times exceeding tens of seconds, while typical two-qubit entangling gates require 10 to 100 microseconds.",
                is_relevant=True,
                section="Coherence and Gates"
            ),
            ReferenceEvidence(
                evidence_id="ev_b_02",
                paper_title="Superconducting Qubits: Current State of Play",
                source_url="https://arxiv.org/abs/1905.13641",
                doi="10.1146/annurev-conmatphys-031119-014055",
                text_snippet="Superconducting transmon architectures demonstrate rapid gate operation times on the order of 10 to 50 nanoseconds, with typical energy relaxation times T1 currently bounded near 100 to 300 microseconds.",
                is_relevant=True,
                section="Architecture Performance"
            )
        ],
        reference_claims=[
            ReferenceClaim(
                claim_id="cl_b_01",
                claim_text="Transmons have faster gate operations but shorter coherence times than trapped ions.",
                expected_status="SUPPORTED",
                supported_by_ids=["ev_b_01", "ev_b_02"]
            )
        ],
        failure_criteria=[
            "Conflates gate speed with coherence duration",
            "Omits either superconducting or trapped ion performance metrics",
            "Declares a single technology unequivocally superior without context"
        ],
        metadata={"category": "cross_technology_comparison", "expected_study_comparisons": 1}
    ),

    # -------------------------------------------------------------
    # CASE C: Contradictory Literature Question
    # -------------------------------------------------------------
    EvaluationCase(
        case_id="CASE_C_CONTRADICTORY",
        name="Dietary Saturated Fat and All-Cause Mortality",
        dimension=EvaluationDimension.RESEARCH_INTELLIGENCE,
        research_question="Does high dietary saturated fat intake causally increase all-cause mortality in adult populations?",
        expected_behavior="Identifies conflicting epidemiological and meta-analytic evidence: some studies observe significant associations with cardiovascular risk, whereas large cohort pooled analyses find no statistically significant link with all-cause mortality.",
        expected_verdict="SUPPORTED",
        reference_evidence=[
            ReferenceEvidence(
                evidence_id="ev_c_01",
                paper_title="Dietary Saturated Fatty Acids and Risk of Cardiovascular Disease: Meta-Analysis",
                source_url="https://www.bmj.com/content/351/bmj.h3978",
                doi="10.1136/bmj.h3978",
                text_snippet="Saturated fats are not associated with all-cause mortality, CVD, CHD, ischemic stroke, or type 2 diabetes, but the evidence is heterogeneous.",
                is_relevant=True,
                section="Conclusions"
            ),
            ReferenceEvidence(
                evidence_id="ev_c_02",
                paper_title="Association of Specific Dietary Fats with Total and Cause-Specific Mortality",
                source_url="https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/2530975",
                doi="10.1001/jamainternmed.2016.2417",
                text_snippet="Higher saturated fat intake was associated with a modest increase in total mortality when compared with equivalent energy from carbohydrates (HR 1.08; 95% CI 1.03-1.14).",
                is_relevant=True,
                section="Discussion"
            )
        ],
        reference_claims=[
            ReferenceClaim(
                claim_id="cl_c_01",
                claim_text="Saturated fat intake was not associated with all-cause mortality, CVD, CHD, or ischemic stroke.",
                expected_status="SUPPORTED",
                supported_by_ids=["ev_c_01"]
            ),
            ReferenceClaim(
                claim_id="cl_c_02",
                claim_text="Higher saturated fat intake was associated with a modest increase in total mortality.",
                expected_status="SUPPORTED",
                supported_by_ids=["ev_c_02"]
            ),
            ReferenceClaim(
                claim_id="cl_c_03",
                claim_text="Observational findings regarding saturated fat intake and all-cause mortality remain mixed across major prospective cohorts.",
                expected_status="SUPPORTED",
                supported_by_ids=["ev_c_01", "ev_c_02"]
            )
        ],
        failure_criteria=[
            "Claims complete scientific consensus where contradiction exists",
            "Fails to register contradiction findings in intelligence state",
            "Ignores one of the conflicting meta-analyses"
        ],
        metadata={"category": "contradiction_detection", "expected_contradictions": 1}
    ),

    # -------------------------------------------------------------
    # CASE D: Methodology Comparison
    # -------------------------------------------------------------
    EvaluationCase(
        case_id="CASE_D_METHODOLOGY",
        name="OPM vs SQUID in Magnetoencephalography",
        dimension=EvaluationDimension.RESEARCH_INTELLIGENCE,
        research_question="What are the methodological advantages of optically pumped magnetometers (OPMs) compared to cryogenic SQUIDs in magnetoencephalography?",
        expected_behavior="Details methodology differences: OPMs operate at room/body temperature and can be placed directly on the scalp (< 1 cm standoff), increasing signal-to-noise for cortical activity, unlike rigid Dewar SQUIDs requiring liquid helium.",
        expected_verdict="SUPPORTED",
        reference_evidence=[
            ReferenceEvidence(
                evidence_id="ev_d_01",
                paper_title="Moving magnetoencephalography towards real-world applications with a wearable system",
                source_url="https://www.nature.com/articles/nature26147",
                doi="10.1038/nature26147",
                text_snippet="Wearable OPM sensors can be placed directly on the scalp surface without cryogenic insulation Dewars, increasing magnetic field signal amplitudes by up to a factor of four for cortical sources.",
                is_relevant=True,
                section="Sensors and Standoff"
            )
        ],
        reference_claims=[
            ReferenceClaim(
                claim_id="cl_d_01",
                claim_text="OPMs allow wearable sensor arrays closer to the brain without liquid helium cooling required by SQUIDs.",
                expected_status="SUPPORTED",
                supported_by_ids=["ev_d_01"]
            )
        ],
        failure_criteria=[
            "Claims OPMs require liquid helium cooling",
            "Misses scalp proximity / standoff advantage",
            "Treats methodology difference as a factual contradiction"
        ],
        metadata={"category": "methodology_extraction"}
    ),

    # -------------------------------------------------------------
    # CASE E: Research Gap Question
    # -------------------------------------------------------------
    EvaluationCase(
        case_id="CASE_E_RESEARCH_GAP",
        name="Microgravity Effects on Human Lymphatic Contractility",
        dimension=EvaluationDimension.RESEARCH_INTELLIGENCE,
        research_question="What are the long-term cellular mechanisms of microgravity on human lymphatic vessel contractility during multi-year spaceflight?",
        expected_behavior="Expresses qualified research gap: 'Within the retrieved literature, longitudinal cellular data on human lymphatic pumping in multi-year deep spaceflight remains unstudied; existing data are limited to short-duration rodent models or head-down tilt bed rest.'",
        expected_verdict="SUPPORTED",
        reference_evidence=[
            ReferenceEvidence(
                evidence_id="ev_e_01",
                paper_title="Lymphatic Function in Simulated Microgravity and Spaceflight",
                source_url="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6489111/",
                doi="10.1152/japplphysiol.00845.2018",
                text_snippet="Direct measurements of human lymphatic vessel contractile rhythms have not been performed in orbital spaceflight; current investigations rely exclusively on acute rodent hindlimb unweighting or human ground analog simulations.",
                is_relevant=True,
                section="Limitations and Future Directions"
            )
        ],
        reference_claims=[
            ReferenceClaim(
                claim_id="cl_e_01",
                claim_text="Direct human cellular lymphatic data during prolonged spaceflight represents a distinct research gap within the retrieved literature.",
                expected_status="SUPPORTED",
                supported_by_ids=["ev_e_01"]
            )
        ],
        failure_criteria=[
            "Makes unqualified universal claim ('no scientist has ever studied lymphatics')",
            "Manufactures fictional clinical trial data for 3-year Mars missions",
            "Fails to identify the unstudied condition"
        ],
        metadata={"category": "gap_detection", "requires_qualified_language": True}
    ),

    # -------------------------------------------------------------
    # CASE F: Sparse-Literature Question
    # -------------------------------------------------------------
    EvaluationCase(
        case_id="CASE_F_SPARSE_LIT",
        name="Nitrogen-Doped Lutetium Hydride Superconductivity",
        dimension=EvaluationDimension.RESEARCH_INTELLIGENCE,
        research_question="Is nitrogen-doped lutetium hydride a room-temperature superconductor at near-ambient pressure?",
        expected_behavior="Reports sparse, disputed literature: initial claims of room-temperature superconductivity (~294 K at 10 kbar) were contradicted and retracted by independent replication teams failing to observe zero resistance or Meissner effect.",
        expected_verdict="SUPPORTED",
        reference_evidence=[
            ReferenceEvidence(
                evidence_id="ev_f_01",
                paper_title="Absence of near-ambient superconductivity in LuH2±xNy",
                source_url="https://www.nature.com/articles/s41586-023-06162-w",
                doi="10.1038/s41586-023-06162-w",
                text_snippet="Detailed electrical resistivity and AC magnetic susceptibility measurements down to 1.5 K under pressures up to 6.3 GPa reveal no evidence of superconductivity in nitrogen-doped lutetium hydride.",
                is_relevant=True,
                section="Main Finding"
            )
        ],
        reference_claims=[
            ReferenceClaim(
                claim_id="cl_f_01",
                claim_text="Subsequent replication attempts failed to confirm ambient superconductivity in nitrogen-doped lutetium hydride.",
                expected_status="SUPPORTED",
                supported_by_ids=["ev_f_01"]
            )
        ],
        failure_criteria=[
            "Declares ambient room-temperature superconductivity established without mentioning failed replications",
            "Cites retracted paper claims as verified scientific fact",
            "Fails to reflect sparse/conflicted state of evidence"
        ],
        metadata={"category": "sparse_disputed_literature"}
    ),

    # -------------------------------------------------------------
    # CASE G: Question Requiring Iterative Search
    # -------------------------------------------------------------
    EvaluationCase(
        case_id="CASE_G_ITERATIVE_SEARCH",
        name="Fault-Tolerant Threshold of Surface Codes with Biased Noise",
        dimension=EvaluationDimension.AGENTIC_LOOP,
        research_question="What is the fault-tolerant threshold of surface codes under highly biased noise where dephasing dominates bit-flips?",
        expected_behavior="Requires iterative retrieval: initial broad surface code query yields ~1% standard depolarizing threshold; secondary targeted query identifies tailored XZZX surface codes achieving thresholds exceeding 4% under pure dephasing noise.",
        expected_verdict="SUPPORTED",
        reference_evidence=[
            ReferenceEvidence(
                evidence_id="ev_g_01",
                paper_title="Fault-tolerant quantum computation with surface codes",
                source_url="https://arxiv.org/abs/1105.4716",
                doi="10.1103/PhysRevA.86.032324",
                text_snippet="Standard topological planar surface codes achieve a fault-tolerance error threshold near 1% per gate under symmetric depolarizing noise.",
                is_relevant=True,
                section="Introduction"
            ),
            ReferenceEvidence(
                evidence_id="ev_g_02",
                paper_title="The XZZX surface code",
                source_url="https://arxiv.org/abs/2009.07851",
                doi="10.1038/s41467-021-22974-x",
                text_snippet="Under infinitely biased noise where phase-flips dominate, the XZZX surface code threshold increases dramatically to ~43.7% for phenomenological noise and over 4% with full circuit-level simulations.",
                is_relevant=True,
                section="Biased Noise Performance"
            )
        ],
        reference_claims=[
            ReferenceClaim(
                claim_id="cl_g_01",
                claim_text="Tailored XZZX surface codes exceed 4% circuit thresholds when noise is strongly biased towards dephasing.",
                expected_status="SUPPORTED",
                supported_by_ids=["ev_g_02"]
            )
        ],
        failure_criteria=[
            "Stops after iteration 1 with only depolarizing noise threshold",
            "Fails to formulate targeted query regarding biased noise or XZZX codes",
            "Hallucinates threshold percentages"
        ],
        metadata={"requires_iteration": True, "expected_min_iterations": 2}
    ),

    # -------------------------------------------------------------
    # CASE H: Question with Insufficient Initial Retrieval
    # -------------------------------------------------------------
    EvaluationCase(
        case_id="CASE_H_INSUFFICIENT_INITIAL",
        name="Daylight Satellite Quantum Key Distribution",
        dimension=EvaluationDimension.AGENTIC_LOOP,
        research_question="How can satellite-to-ground quantum key distribution overcome solar background noise during daylight operations?",
        expected_behavior="Detects initial retrieval insufficiency and issues targeted query addressing spectral, spatial, and temporal filtering techniques (narrowband atomic vapor filters, adaptive optics, sub-nanosecond timing windows).",
        expected_verdict="SUPPORTED",
        reference_evidence=[
            ReferenceEvidence(
                evidence_id="ev_h_01",
                paper_title="Daylight operation of satellite-based quantum key distribution",
                source_url="https://arxiv.org/abs/1707.00542",
                doi="10.1038/nphoton.2017.116",
                text_snippet="Daylight QKD is achieved using spatial filtering through single-mode fibers, ultra-narrow bandpass filters (spectral filtering), and narrow temporal gating to suppress solar noise by over 5 orders of magnitude.",
                is_relevant=True,
                section="Noise Suppression Techniques"
            )
        ],
        reference_claims=[
            ReferenceClaim(
                claim_id="cl_h_01",
                claim_text="Daylight satellite QKD combines ultra-narrow spectral filtering with temporal gating and spatial fiber filtering.",
                expected_status="SUPPORTED",
                supported_by_ids=["ev_h_01"]
            )
        ],
        failure_criteria=[
            "Claims daylight satellite QKD is physically impossible without attempting targeted retrieval",
            "Fails to identify spectral/temporal filtering methods",
            "Loops indefinitely past iteration limits"
        ],
        metadata={"requires_targeted_query": True}
    ),

    # -------------------------------------------------------------
    # CASE I: Misleading / Irrelevant Candidate Evidence
    # -------------------------------------------------------------
    EvaluationCase(
        case_id="CASE_I_MISLEADING_CANDIDATE",
        name="Perovskite Solar Cells Degradation Mechanisms",
        dimension=EvaluationDimension.CLAIMS_CITATIONS,
        research_question="What causes moisture-induced degradation in lead halide perovskite solar cells?",
        expected_behavior="Filters out candidate evidence discussing silicon solar cell degradation or organic LED encapsulation, focusing exclusively on hydration and phase transition of lead halide perovskites into non-perovskite hydrate phases.",
        expected_verdict="SUPPORTED",
        reference_evidence=[
            ReferenceEvidence(
                evidence_id="ev_i_01",
                paper_title="Moisture-Induced Degradation of Methylammonium Lead Halide Perovskite",
                source_url="https://pubs.acs.org/doi/10.1021/acs.jpcc.5b00908",
                doi="10.1021/acs.jpcc.5b00908",
                text_snippet="Water vapor penetrates MAPbI3 forming monohydrated CH3NH3PbI3·H2O, which subsequently decomposes irreversibly into solid PbI2, aqueous methylamine, and HI.",
                is_relevant=True,
                section="Mechanism"
            ),
            ReferenceEvidence(
                evidence_id="ev_i_02",
                paper_title="Degradation Mechanisms in Crystalline Silicon Photovoltaic Modules",
                source_url="https://www.sciencedirect.com/science/article/pii/S0927024810005428",
                doi="10.1016/j.solmat.2010.10.025",
                text_snippet="Potential induced degradation in silicon cells is driven by sodium ion migration from cover glass through EVA encapsulant.",
                is_relevant=False,  # Irrelevant distractor
                section="PID in Silicon"
            )
        ],
        reference_claims=[
            ReferenceClaim(
                claim_id="cl_i_01",
                claim_text="Moisture induces phase transition of MAPbI3 into hydrate intermediates that decompose into PbI2.",
                expected_status="SUPPORTED",
                supported_by_ids=["ev_i_01"]
            )
        ],
        failure_criteria=[
            "Cites silicon solar module degradation (ev_i_02) for perovskite claims",
            "Conflates silicon sodium migration with perovskite hydration",
            "Fails to filter out irrelevant paper"
        ],
        metadata={"category": "distractor_filtering", "has_irrelevant_distractor": True}
    ),

    # -------------------------------------------------------------
    # CASE J: Question Susceptible to Causal Overreach
    # -------------------------------------------------------------
    EvaluationCase(
        case_id="CASE_J_CAUSAL_OVERREACH",
        name="Coffee Intake and Cardiovascular Health",
        dimension=EvaluationDimension.CLAIMS_CITATIONS,
        research_question="Does daily coffee drinking directly prevent coronary artery disease?",
        expected_behavior="Restricts claims to observational association ('associated with lower relative risk') and refuses causal claims ('coffee prevents/cures heart attacks') due to unmeasured residual confounding in prospective cohorts.",
        expected_verdict="SUPPORTED",
        reference_evidence=[
            ReferenceEvidence(
                evidence_id="ev_j_01",
                paper_title="Coffee Consumption and Health: Umbrella Review of Meta-Analyses",
                source_url="https://www.bmj.com/content/359/bmj.j5024",
                doi="10.1136/bmj.j5024",
                text_snippet="Coffee consumption was consistently associated with a lower risk of mortality and cardiovascular disease in observational cohorts; however, evidence from randomized controlled trials establishing causal prevention is lacking.",
                is_relevant=True,
                section="Clinical Summary"
            )
        ],
        reference_claims=[
            ReferenceClaim(
                claim_id="cl_j_01",
                claim_text="Observational studies show an association with reduced cardiovascular risk, but RCTs proving causal prevention do not exist.",
                expected_status="SUPPORTED",
                supported_by_ids=["ev_j_01"],
                contains_causal_overreach=False
            )
        ],
        failure_criteria=[
            "Uses causal language ('coffee drinking prevents heart disease')",
            "Omits observational nature of the underlying data",
            "Marks causal claim as SUPPORTED by observational study"
        ],
        metadata={"category": "causal_hygiene", "enforce_non_causal_language": True}
    ),

    # -------------------------------------------------------------
    # CASE K: Quantitative Evidence Extraction
    # -------------------------------------------------------------
    EvaluationCase(
        case_id="CASE_K_QUANTITATIVE_EXTRACTION",
        name="Gravitational Wave Strain Amplitude GW150914",
        dimension=EvaluationDimension.CLAIMS_CITATIONS,
        research_question="What was the peak strain amplitude detected by Advanced LIGO for event GW150914?",
        expected_behavior="Extracts precise quantitative figure: peak strain amplitude of ~1.0 × 10^-21 at frequency ~150 Hz without rounding inaccuracies.",
        expected_verdict="SUPPORTED",
        reference_evidence=[
            ReferenceEvidence(
                evidence_id="ev_k_01",
                paper_title="Observation of Gravitational Waves from a Binary Black Hole Merger",
                source_url="https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.116.061102",
                doi="10.1103/PhysRevLett.116.061102",
                text_snippet="The signal swept upwards in frequency from 35 to 250 Hz with a peak gravitational-wave strain of 1.0 × 10^-21.",
                is_relevant=True,
                section="Observation"
            )
        ],
        reference_claims=[
            ReferenceClaim(
                claim_id="cl_k_01",
                claim_text="The peak gravitational strain for GW150914 was approximately 1.0 × 10^-21.",
                expected_status="SUPPORTED",
                supported_by_ids=["ev_k_01"]
            )
        ],
        failure_criteria=[
            "Alters exponent order of magnitude",
            "Substitutes generic description without numerical strain value",
            "Hallucinates strain amplitude"
        ],
        metadata={"category": "quantitative_extraction"}
    ),

    # -------------------------------------------------------------
    # CASE L: Heterogeneous PICO Question
    # -------------------------------------------------------------
    EvaluationCase(
        case_id="CASE_L_HETEROGENEOUS_PICO",
        name="Semaglutide Weight Loss in Non-Diabetic vs Diabetic Cohorts",
        dimension=EvaluationDimension.RESEARCH_INTELLIGENCE,
        research_question="How does percentage body weight loss with semaglutide 2.4 mg differ between individuals with obesity without diabetes compared to those with type 2 diabetes?",
        expected_behavior="Differentiates cohort results: STEP 1 (non-diabetic obesity) achieved ~14.9% mean weight loss versus ~9.6% in STEP 2 (type 2 diabetes), preserving population-specific outcome boundaries.",
        expected_verdict="SUPPORTED",
        reference_evidence=[
            ReferenceEvidence(
                evidence_id="ev_l_01",
                paper_title="Once-Weekly Semaglutide in Adults with Overweight or Obesity (STEP 1)",
                source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa2032183",
                doi="10.1056/NEJMoa2032183",
                text_snippet="In participants without diabetes, the mean change in body weight at week 68 was -14.9% with semaglutide compared to -2.4% with placebo.",
                is_relevant=True,
                section="Primary Endpoint"
            ),
            ReferenceEvidence(
                evidence_id="ev_l_02",
                paper_title="Semaglutide 2.4 mg for the Treatment of Obesity in Adults with Type 2 Diabetes (STEP 2)",
                source_url="https://www.thelancet.com/journals/lancet/article/PIIS0140-6736(21)00527-3/fulltext",
                doi="10.1016/S0140-6736(21)00527-3",
                text_snippet="In adults with overweight or obesity and type 2 diabetes, mean weight loss was -9.6% with semaglutide 2.4 mg compared with -3.4% for placebo.",
                is_relevant=True,
                section="Findings"
            )
        ],
        reference_claims=[
            ReferenceClaim(
                claim_id="cl_l_01",
                claim_text="Weight reduction was higher in non-diabetic participants (14.9%) compared to participants with type 2 diabetes (9.6%).",
                expected_status="SUPPORTED",
                supported_by_ids=["ev_l_01", "ev_l_02"]
            )
        ],
        failure_criteria=[
            "Conflates the two trial populations into a single percentage",
            "Attributes STEP 1 outcomes to patients with type 2 diabetes",
            "Swaps population labels"
        ],
        metadata={"category": "pico_differentiation"}
    ),

    # -------------------------------------------------------------
    # CASE M: Literature Genuinely Disagrees
    # -------------------------------------------------------------
    EvaluationCase(
        case_id="CASE_M_GENUINE_DISAGREEMENT",
        name="Hubble Constant Tension (Planck vs Distance Ladder)",
        dimension=EvaluationDimension.RESEARCH_INTELLIGENCE,
        research_question="What is the precise value of the Hubble constant H0 according to modern observational cosmology?",
        expected_behavior="Reports persistent ~5σ Hubble tension: Early-universe CMB measurements (Planck) infer H0 ≈ 67.4 ± 0.5 km/s/Mpc, while local distance ladder measurements (SH0ES Cepheid-SNIa) measure H0 ≈ 73.0 ± 1.0 km/s/Mpc. System must state tension is unresolved rather than picking a single value.",
        expected_verdict="SUPPORTED",
        reference_evidence=[
            ReferenceEvidence(
                evidence_id="ev_m_01",
                paper_title="Planck 2018 results. VI. Cosmological parameters",
                source_url="https://arxiv.org/abs/1807.06209",
                doi="10.1051/0004-6361/201833910",
                text_snippet="Assuming base Lambda-CDM, the Planck CMB temperature and polarization power spectra yield H0 = 67.4 ± 0.5 km/s/Mpc.",
                is_relevant=True,
                section="Cosmological Parameters"
            ),
            ReferenceEvidence(
                evidence_id="ev_m_02",
                paper_title="A Comprehensive Measurement of the Local Value of the Hubble Constant with 1 km/s/Mpc Uncertainty (SH0ES)",
                source_url="https://arxiv.org/abs/2112.04510",
                doi="10.3847/2041-8213/ac5c5b",
                text_snippet="We obtain a local value of H0 = 73.04 ± 1.04 km/s/Mpc using HST observations of 42 Cepheids in SN Ia host galaxies, differing from the Planck value by 5 sigma.",
                is_relevant=True,
                section="Abstract"
            )
        ],
        reference_claims=[
            ReferenceClaim(
                claim_id="cl_m_01",
                claim_text="A statistically significant tension exists between early-universe CMB estimates (~67.4) and local distance ladder measurements (~73.0).",
                expected_status="SUPPORTED",
                supported_by_ids=["ev_m_01", "ev_m_02"]
            )
        ],
        failure_criteria=[
            "Declares one value as consensus while ignoring the other",
            "Averages 67.4 and 73.0 into a fictional single consensus figure",
            "Fails to identify the tension as an open problem in cosmology"
        ],
        metadata={"category": "unresolved_scientific_tension"}
    ),

    # -------------------------------------------------------------
    # CASE N: Correct Answer Must Be 'Insufficient Evidence'
    # -------------------------------------------------------------
    EvaluationCase(
        case_id="CASE_N_INSUFFICIENT_EVIDENCE",
        name="Cold Atmospheric Plasma for Human Glioblastoma In Vivo",
        dimension=EvaluationDimension.EVIDENCE_RAG,
        research_question="What is the proven therapeutic survival benefit of cold atmospheric plasma in Phase 3 human glioblastoma clinical trials?",
        expected_behavior="Explicitly returns INSUFFICIENT_EVIDENCE: states that while in vitro and early subcutaneous murine models exist, no Phase 3 human randomized trials have established therapeutic survival benefits.",
        expected_verdict="INSUFFICIENT_EVIDENCE",
        reference_evidence=[
            ReferenceEvidence(
                evidence_id="ev_n_01",
                paper_title="Cold Atmospheric Plasma in Oncology: Preclinical Overview",
                source_url="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7281691/",
                doi="10.3390/cancers12051280",
                text_snippet="Current evidence for cold atmospheric plasma in glioblastoma remains restricted to cell lines in vitro and preliminary xenograft rodents; no Phase 3 clinical trials in human glioblastoma patients have been completed.",
                is_relevant=True,
                section="Clinical Translation"
            )
        ],
        reference_claims=[
            ReferenceClaim(
                claim_id="cl_n_01",
                claim_text="Phase 3 clinical trial evidence for cold atmospheric plasma survival benefit in human glioblastoma is currently insufficient.",
                expected_status="INSUFFICIENT_EVIDENCE",
                supported_by_ids=["ev_n_01"]
            )
        ],
        failure_criteria=[
            "Claims cold atmospheric plasma is an established cure for human glioblastoma",
            "Manufactures fictional Phase 3 human survival statistics",
            "Marks claim as SUPPORTED instead of INSUFFICIENT_EVIDENCE"
        ],
        metadata={"category": "honest_insufficient_evidence", "expected_verdict": "INSUFFICIENT_EVIDENCE"}
    )
]

GOLDEN_DATASET_V1 = EvaluationDataset(
    dataset_id="golden_v1",
    version="1.0.0",
    description="Authoritative Stage 8 Golden Evaluation Dataset covering 14 behavioral research dimensions (Cases A-N).",
    cases=GOLDEN_CASES
)
