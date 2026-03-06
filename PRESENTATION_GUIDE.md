# KLR.ai Project Presentation Guide (30-40 Minutes)

## 1) Project Description (What KLR.ai Is)
KLR.ai is an assistive-vision system designed to improve spatial awareness for visually impaired users. The system captures a camera frame, runs object detection and depth estimation, calculates collision risk, and generates spoken/typed guidance using an LLM.

Core flow:
1. Frontend captures an image.
2. Backend decodes and processes it.
3. Perception pipeline runs YOLO + spatial estimation.
4. LLM converts structured scene data into actionable guidance.
5. Optional text-to-speech plays the response.

## 2) What To Say In The Introduction (1-3 Minutes)
Use this structure:
1. Problem statement:
   "People with limited vision need fast, contextual awareness of nearby obstacles and objects."
2. Product statement:
   "KLR.ai is a real-time assistive-vision pipeline that turns camera input into safety-oriented natural language guidance."
3. Your role:
   "I inherited a hackathon prototype and focused on refactoring it into a maintainable, production-style architecture while preserving behavior."
4. Thesis for presentation:
   "This project is about converting an impressive demo into a system that is modular, testable, and ready for performance optimization."

## 3) 30-40 Minute Itinerary

### Option A: 30 Minutes
1. 0:00-2:00 - Intro and problem context.
2. 2:00-6:00 - Demo / user journey (camera -> guidance).
3. 6:00-12:00 - Architecture walkthrough (frontend, API, app_core, perception, integrations).
4. 12:00-18:00 - Deep dive: perception pipeline and orchestration.
5. 18:00-23:00 - Refactor decisions and why they matter.
6. 23:00-27:00 - Challenges + problem-solving stories.
7. 27:00-30:00 - Key learnings, next steps, Q&A.

### Option B: 40 Minutes
1. 0:00-3:00 - Intro and objective.
2. 3:00-9:00 - End-to-end demo + request/response flow.
3. 9:00-17:00 - System architecture and module boundaries.
4. 17:00-24:00 - Technical deep dive (pipeline stages, fallback behavior, timings/trace IDs).
5. 24:00-31:00 - Engineering challenges and tradeoffs.
6. 31:00-36:00 - Lessons learned and what you would redesign next.
7. 36:00-40:00 - Q&A with prepared backup slides.

## 4) Suggested Slide Outline
1. Title: KLR.ai - From Hackathon Prototype to Maintainable System.
2. User problem and why it matters.
3. End-to-end flow diagram.
4. Architecture layers (apps / services / integrations / tools).
5. API design and request lifecycle.
6. Perception pipeline deep dive (YOLO, depth, collision scoring).
7. LLM integration and response generation.
8. Observability (timings, trace_id, stage-level visibility).
9. Challenges encountered.
10. How you solved them.
11. What you learned.
12. Next phase: latency optimization and production hardening.

## 5) Key Challenges You Can Discuss
1. Tight coupling in inherited code.
   - Symptom: routing, inference, and vendor SDK logic mixed together.
   - Impact: hard to test, hard to replace components, fragile changes.
2. Inconsistent module boundaries/imports.
   - Symptom: path hacks and blurred ownership.
   - Impact: onboarding friction and integration bugs.
3. Latency concentration in single synchronous path.
   - Symptom: decode + YOLO + depth + LLM all in one request.
   - Impact: slower user feedback.
4. Inconsistent API behavior and error handling.
   - Symptom: varying response shapes and failure modes.
   - Impact: frontend complexity and reduced reliability.
5. Limited observability.
   - Symptom: little stage-level timing visibility initially.
   - Impact: optimization discussions were guess-based.

## 6) How You Problem-Solved Around Those Challenges
1. Refactored by layers (API, app_core, perception, integrations).
   - Why it worked: each layer now has a clear responsibility.
2. Built modular perception stages.
   - Why it worked: YOLO and spatial logic can be tested/replaced independently.
3. Isolated vendor integrations.
   - Why it worked: Azure/ElevenLabs concerns no longer leak into business logic.
4. Standardized endpoint patterns and response metadata.
   - Why it worked: easier frontend integration and debugging.
5. Added timing/trace instrumentation.
   - Why it worked: provided evidence for where optimization should happen next.

## 7) Reflection Questions (To Prepare Your "What I Learned" Section)

### Architecture and Design
1. What design decision most reduced future complexity?
2. Which module boundaries were the hardest to define, and why?
3. If you restarted this project, what would you design differently on day 1?

### Engineering Process
1. How did you decide what to refactor first vs later?
2. What tradeoff did you accept between speed and code quality?
3. What signals told you the refactor was actually improving maintainability?

### Problem Solving
1. Describe one bug/issue where the first fix failed. What changed in your second approach?
2. Which bottleneck did you first suspect for latency, and what data confirmed/refuted that?
3. How did you reduce risk while changing a live/inherited codebase?

### Product/User Thinking
1. How did user safety shape your technical choices?
2. What does "good enough" response quality mean for assistive guidance?
3. Where is the line between model intelligence and deterministic safety rules?

### Team/Communication
1. How would you explain this architecture to a new teammate in 5 minutes?
2. What decisions would you document as ADRs (Architecture Decision Records)?
3. What work should be parallelized across teammates in the next iteration?

## 8) Strong "What I Learned" Talking Points (Examples)
1. Maintainability is a feature: clearer module boundaries directly improve delivery speed.
2. Instrumentation before optimization: timing data prevented premature optimization.
3. Integration isolation matters: external SDKs change often; adapters reduce blast radius.
4. Refactoring inherited code requires preserving behavior while changing structure.
5. In ML-enabled systems, deterministic fallbacks and guardrails are as important as model quality.

## 9) Next Steps You Can Present
1. Model warm-up and singleton lifecycle management.
2. Reduce duplicate transforms and image transcoding overhead.
3. Async/background processing mode for heavy stages.
4. Stronger test coverage for pipeline stages and failure paths.
5. Better benchmarking for latency/quality across models and prompts.

## 10) 60-Second Closing Script
"KLR.ai started as a promising hackathon prototype. My contribution was to turn that prototype into a system with clear boundaries, measurable behavior, and a path to production optimization. The biggest lesson was that architecture and observability are what make iteration sustainable, especially in AI systems where multiple components can fail or add latency. The next phase is performance hardening and evaluation discipline so the system can become reliably useful in real-world assistive scenarios."
