---
id: 2026-11-15-fund-setup-trade-ideas-and-structure
type: meeting
title: "Meeting: fund setup, trade ideas and structure"
date: 2026-11-15
authors: [DarkEB1]
owner: DarkEB1
status: draft
tags: [idea, risk, portfolio, equities]
related: [2026-10-28-kickoff]
---

# Meeting: fund setup, trade ideas and structure

Recording: none.

## Attendees

First names only: this repository is public and nobody but @DarkEB1 has a handle in
`knowledge/context/team.yaml` yet.

- James
- Fenton
- Nicholas
- Claudio
- Lucas

## Agenda

1. Overview: fund name, what we do, repo setup
2. Trade ideas (micro-cap shorts, quantum)
3. Fund structure, risk and voting
4. Todos and allocations

## Notes

### Trade ideas

- Micro-cap shorts look underpriced as a mean-reversion play. Open questions: how to manage risk
  on a book of these trades, how they backtest, and whether borrow costs eat the whole premium.
- Quantum shorts and higher-order derivatives could be interesting, though they are long-horizon
  plays.

### Fund structure

- Simple-majority votes on every trade were judged a poor way to run the book.
- Proposal: idea pods. Each member runs their own book within a mandate, maximum position limits
  and risk limits. Half of the fund is split between all members as these books.
- A member can add to their cap by proposing a trade to the others and tapping the shared pool.
  How the vote on such a proposal works is still open.
- The cap is on sizing, not on risk: each member's risk understanding goes into the Kelly
  criterion and the result caps the position size. Risk understanding here means market risk plus
  the spread the member believes is under- or overvalued, not market risk alone.
- None of this works without auditable trade records, NAV and PnL.

## Decisions

- The fund is called Shrubbery Capital Advisory and Management (SCAAM) (minor)
- Simple-majority votes on every trade are out; work towards idea pods with per-member books. The pod limits, the Kelly sizing cap and the pool vote become an ADR once the risk + voting action below returns a proposal (minor)

## Actions

Owners are first names until they have handles, and no dates were set. Unclaimed items are open
for anyone to take.

- [ ] Data access: James (@TODO-owner, TODO-date)
- [ ] Data availability: Fenton (@TODO-owner, TODO-date)
- [ ] Risk framework, voting, and the motivation for people to be here: Nick (@TODO-owner, TODO-date)
- [ ] Backtesting framework: Alec and Lucas (@TODO-owner, TODO-date)
- [ ] Brokerage account research and setup: Eduardo (@TODO-owner, TODO-date)
- [ ] Fund structure (legal set-up, given most members are students and on visas): unclaimed (@TODO-owner, TODO-date)
- [ ] Auditable trade records, NAV and PnL: unclaimed (@TODO-owner, TODO-date)
- [ ] Claudio: no preference, to pick up an unclaimed item (@TODO-owner, TODO-date)
- [ ] Everyone who has not yet: set yourself up with the GitHub repo, see [start-here](../context/start-here.md) (@TODO-owner, TODO-date)
