---
name: draft-prompt
description: "Turn a rough request into a prompt for a reader without this conversation, confirm requirements before doing the work here, or improve an existing prompt."
disable-model-invocation: true
---

# Draft Prompt

## Purpose

Turn a rough description of work that has not started yet into what the next step needs: a self-contained prompt for a reader who cannot see this conversation, a requirements check before doing the work here, or a revised version of an existing prompt. To pass on work already in progress, use the `handoff` skill instead.

The value comes from surfacing what only the user knows (audience, scope, what done looks like, a preference between reasonable approaches) and from giving the receiver a way to check its result. Rewording alone adds little when the same model, with the same context, will do the work.

## Choose the Mode

Pick the mode from the arguments and the request. Ask only when the request fits more than one mode and the choice would change the output.

- **Handoff prompt**: the receiver lacks this conversation. It may be another Claude session, a subagent, Codex or another agent, or a system prompt sent through the API.
- **Confirm here**: the user wants the work done in this session.
- **Improve**: the user supplies an existing prompt, pasted or as a file path.

## Handoff Prompt

Write a prompt the receiver can act on with nothing else. Read it as a colleague who has never seen this conversation would: wherever they would have to ask what a term, file, or decision means, put the answer in the prompt.

Cover what the task needs from this list:

- The goal, and the purpose behind it when that shapes judgment calls.
- Context only the user or this session has: environment, relevant files and paths, decisions already made and why, approaches already ruled out.
- Scope and constraints, each with its reason when the reason is not obvious.
- The shape of the deliverable.
- How to verify: completion criteria and a check the receiver can run, such as a test command, a spec to compare against, or a pass condition. If no check exists, say so in the prompt so the receiver knows its result is unchecked.

Match the format to the receiver. For Claude, structure longer prompts with XML tags such as `<context>`, `<task>`, and `<constraints>`. For Codex or other GPT-family models, use Markdown sections such as `# Context` and `# Task`. A short task needs only a paragraph, whoever the receiver is. If the user does not name the receiver, assume another Claude session and state that assumption in one line above the prompt.

State constraints plainly and give their reasons rather than raising emphasis. Describe outcomes instead of scripting steps the receiver can plan for itself, and number steps only where order matters. Leave out general advice the receiver already follows, such as "be accurate" or "be thorough", along with scaffolds written for older models: scratchpad tags, "think step by step", and response prefills.

## Confirm Here

Skip the prompt. In a few lines, restate the goal, what done looks like and how it will be checked, and the assumptions you would otherwise act on. Then ask only the questions whose answers would change the result. Wait for the user to confirm or correct before starting the work.

## Improve

Read the prompt as its receiver would and find what stands between it and a good result: missing context, ambiguous requirements, completion criteria that cannot be checked, constraints without reasons, and instructions that contradict each other. Return the revised prompt, then a short list of what changed and why. Keep the author's wording where it already works.

Patterns written for older Claude models, such as heavy emphasis, step scripts for judgment tasks, scratchpad tags, or prefills, are the subject of a separate audit. When the prompt shows them, point the user to `/claude-api prompt-audit <path>` instead of reproducing that audit here.

## Output

- Give the best draft first instead of opening with questions. Afterward, add one to three questions only when an answer would materially change the prompt.
- Put the prompt in a single fenced code block so it can be copied. If the prompt contains fences, use a longer outer fence.
- Add no facts the user did not provide. When the task depends on material the user has not supplied, such as documents, data, or logs, name what is missing instead of writing around it.
- Keep the prompt for a simple request short. Do not force a template onto it.
- Write the prompt in the language the user asks for, or else in the language the user writes in.
