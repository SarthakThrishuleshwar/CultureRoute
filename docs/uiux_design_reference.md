# CultureRoute UI/UX template adaptation

## What the recording shows

The supplied 28.8-second recording scrolls one Acme landing page. It is a visual reference, not a CultureRoute requirements source. The page uses a near-white warm paper background with subtle grain, charcoal display text with a hand-drawn feel, deep red emphasis, yellow sticky-note callouts, navy/red doodle marks, slim underline strokes, outlined buttons, irregular quote/card frames, and a spacious editorial grid. Its scroll sequence is hero → proof numbers → features → illustrated story cards → three-step process → benefits → testimonials → pricing → FAQ → closing call to action.

## Adaptation map

| Recorded template element | CultureRoute replacement | Why |
| --- | --- | --- |
| Acme logo and team headline | CultureRoute wordmark; “Explore the culture behind every route” | Establishes the actual project and research focus. |
| “Start free trial” / “Watch demo” | “Explore Jaipur” / “Open DEV Lab” | Corresponds to the two proposed experiences. |
| Company adoption and uptime stats | 45 cities, 675 attractions, 411 trips, all labeled study scope | Avoids invented commercial proof. |
| Generic team-feature grid | Discover, build, compare, insights, DEV Lab, traceability | Maps to the six required screens. |
| Blog illustrations | Four photographic cards for heritage, museums, religious sites, and food experiences | Covers the study categories without claiming real bookings. |
| Three-step process | Discover a city → build a day → inspect the evidence | Reflects traveler and evaluator workflows. |
| Testimonials | Method and provenance cards | No supplied user testimonials exist. |
| Pricing plans | “Two ways to explore”: Traveler and Evaluator | The specification does not define prices or subscriptions. |
| FAQ and closing CTA | Questions about data, accessibility, feasibility, forecasts; planner/lab CTA | Answers project-specific questions. |

## Design tokens for the prototype

| Token | Value | Use |
| --- | --- | --- |
| Paper | `#f7f3e9` | Page background |
| Ink | `#292925` | Main text |
| Oxblood | `#982b32` | Emphasis and accents |
| Muted ink | `#746f68` | Secondary copy |
| Sticky note | `#eee3a6` | Scope and caveat callouts |
| Line | `#b6afa3` | Card borders and rules |
| Blue sketch | `#526376` | Diagram and illustration contrast |

## Six-screen UI contract

1. **Project Overview:** research question, SDG connection and limitation, study scope, synthetic-data notice, start points.
2. **Discover a City:** city picker, category/price/step-free filters, map, 15-attraction catalog, cultural share, guide languages/specialties, matrix-coverage warning.
3. **Build a Cultural Day:** date/start/budget/hours/stops/preferences, eligibility feedback, paired map and timetable, itemized cost and estimated between-stop carbon.
4. **Compare Plans:** same-input comparison of Fastest plan and Most cultural stops; aligned maps, schedule, cost, duration, carbon, and coverage caveats.
5. **Insights and Predictions:** city/category filters, weekly/monthly time scope, Chart/Table/How calculated tabs, sample size, numerator and denominator, forecast cutoff, actuals, prediction and MAE.
6. **DEV Lab:** table/view selector, schema/row counts/missingness, Guided and bounded read-only SQL modes, before/after output, command/provenance, match counts, chart, CSV/Parquet export.

The companion [`site/dist/index.html`](../site/dist/index.html) demonstrates the **landing-page visual direction**. It does not implement the six application screens or connect to the source database. The detailed screen behaviors above are design requirements for the eventual UI/UX document and application.

The landing page uses the supplied green landscape photograph in the hero, plus the supplied fort, ornate interior, Golden Temple, and food images in the category cards. The photos enlarge and gain a warm glow on hover; reduced-motion settings remove the enlargement. The supplied cliffside monastery photograph is not used because it appears to show a location outside the study's India-only scope. The photographs are visual references, not evidence that particular attractions appear in the synthetic source tables.
