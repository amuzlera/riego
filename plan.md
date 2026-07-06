
  # Riego Refactor Plan: Local-Only Stack with Better ESP32 Error Containment

  ## Summary

  Refactor the project into a single local workflow where the app talks directly to the ESP32 or simulator, and the ESP32 remains inspectable over the network even when logic errors happen. Remove the EC2/
  log-forwarding model, simplify the app into one mode, and harden the ESP32 enough that most runtime failures are captured into logs/files instead of disappearing to USB-only output.

  ## Key Changes

  - Simplify to one mode:
      - one configurable ESP_HOST
      - no remote mode
      - no EC2 polling, log forwarding, or remote action queue

  - Keep the app as the operator surface:
      - view logs
      - browse/read/edit files
      - control relays/zones
      - inspect status and errors

  - Harden ESP32 error handling without building a heavy safe mode:
      - catch exceptions around endpoint handlers and task loops
      - write tracebacks to persistent log files
      - expose those logs through network endpoints the app can read
      - capture startup/import failures into the same inspectable log path
      - keep crash containment simple: continue serving file/log endpoints where possible

  - Preserve network debuggability:
      - the app should be able to pull logs and files from the ESP32 even after a logic failure
      - USB should only be a fallback, not the primary debugging path

  - Keep the simulator as the primary test harness:
      - use it to validate app behavior and error-reporting flows before touching real hardware

  ## Refactor Stages

  1. Project inventory and target contract
      - list current app routes and ESP32 endpoints
      - mark keep/remove/rename decisions
      - define the final local-only request/response contract

  2. App simplification
      - remove remote-mode and EC2-specific behavior
      - collapse config to a single ESP32 target
      - simplify frontend/API calls to match the final ESP32 contract

  3. ESP32 resilience pass
      - add central exception capture for task loops and endpoint handlers
      - persist tracebacks and crash context to logs/files
      - make file/log/status endpoints available for inspection even after partial failures
      - keep the design lightweight and avoid a large “safe mode” subsystem

  4. Simulator alignment
      - make the simulator mimic the final local-only ESP32 behavior
      - verify that error logs, tracebacks, and file inspection work through the app
      - use it to reproduce failures without USB

  5. Cleanup and stabilization
      - remove dead code, legacy docs, and unused compatibility layers
      - update quickstart/dev scripts for the local-only flow
      - document the debugging workflow: app first, USB last

  ## Error-Handling Goals for ESP32

  - Contain exceptions where they occur:
      - route handlers
      - scheduled tasks
      - startup/import path

  - Preserve observability:
      - traceback goes to persistent log file
      - app can read/tail that file over the network
      - any fatal startup issue is written before the process exits or resets

  - Keep recovery simple:
      - on non-fatal errors, log and continue
      - on repeated failures, allow a controlled reboot or restart only if necessary

  - Avoid complexity:
      - no elaborate mode switching
      - no separate recovery state machine unless a concrete bug demands it

  ## Test Plan

  - App against simulator:
      - list files
      - read and edit files
      - tail logs
      - toggle zones
      - trigger a controlled endpoint error and confirm the traceback is visible through the app

  - ESP32 resilience checks:
      - raise a logic exception in a task and confirm it is logged persistently
      - confirm file/log endpoints still answer after the error
      - confirm startup/import failures are captured into the log path

  - Regression checks:
      - no EC2 calls remain
      - no send_logs-style forwarding remains
      - single-mode app behavior works against simulator and real ESP32 by changing only ESP_HOST

  ## Assumptions

  - The project goal is local-first and network-debuggable, not cloud-connected.
  - The ESP32 should remain simple and not grow a complex recovery framework.
  - The simulator remains the main development and validation target.
  - It is acceptable to change or remove legacy routes if they do not fit the simplified contract.