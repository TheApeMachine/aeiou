local M = {}

-- Signal processing and quorum logic for multi-signal fusion
-- Composable predicates that decide when to escalate issues

local signals = {}  -- Store recent signals
local max_signals = 100  -- Keep last 100 signals

local function add_signal(signal_type, data, severity)
  table.insert(signals, {
    type = signal_type,
    data = data,
    severity = severity or "low",
    timestamp = os.time()
  })

  -- Keep only recent signals
  if #signals > max_signals then
    table.remove(signals, 1)
  end
end

-- Predicate functions for different conditions
local predicates = {
  duplication_high = function(signal)
    return signal.type == "analysis" and
           signal.data.duplication and
           signal.data.duplication > 5
  end,

  complexity_high = function(signal)
    return signal.type == "analysis" and
           signal.data.complexity and
           signal.data.complexity.complexity_score > 50
  end,

  test_gap_large = function(signal)
    return signal.type == "analysis" and
           signal.data.test_gap and
           signal.data.test_gap.test_coverage_ratio < 0.3
  end,

  todos_many = function(signal)
    return signal.type == "analysis" and
           signal.data.todos_dead_code and
           signal.data.todos_dead_code.todos > 3
  end,

  recent_file_changes = function(signals_list)
    local recent_changes = 0
    local now = os.time()
    for _, sig in ipairs(signals_list) do
      if sig.type == "FILE_SAVED" and (now - sig.timestamp) < 3600 then -- last hour
        recent_changes = recent_changes + 1
      end
    end
    return recent_changes > 2
  end,

  user_idle_long = function(signals_list)
    local recent_idle = 0
    local now = os.time()
    for _, sig in ipairs(signals_list) do
      if sig.type == "USER_IDLE" and (now - sig.timestamp) < 300 then -- last 5 minutes
        recent_idle = recent_idle + 1
      end
    end
    return recent_idle > 3
  end
}

-- Quorum rules: combinations of predicates that trigger escalation
local quorum_rules = {
  {
    name = "code_quality_concern",
    predicates = {"duplication_high", "complexity_high"},
    threshold = 2,  -- Need 2 out of 2 predicates to match
    severity = "medium",
    action = "suggest_refactor"
  },
  {
    name = "testing_gap",
    predicates = {"test_gap_large", "todos_many"},
    threshold = 1,  -- Need 1 out of 2 predicates to match
    severity = "low",
    action = "suggest_tests"
  },
  {
    name = "high_activity_period",
    predicates = {"recent_file_changes", "user_idle_long"},
    threshold = 2,
    severity = "high",
    action = "pause_suggestions"
  }
}

function M.process_signal(signal_type, data, severity)
  add_signal(signal_type, data, severity)

  -- Check if any quorum rules are triggered
  local triggered_rules = {}

  for _, rule in ipairs(quorum_rules) do
    local matches = 0

    for _, pred_name in ipairs(rule.predicates) do
      local predicate = predicates[pred_name]
      if predicate then
        if pred_name == "recent_file_changes" or pred_name == "user_idle_long" then
          -- These predicates need the full signal list
          if predicate(signals) then
            matches = matches + 1
          end
        else
          -- Check against the current signal
          if predicate({type = signal_type, data = data}) then
            matches = matches + 1
          end
        end
      end
    end

    if matches >= rule.threshold then
      table.insert(triggered_rules, {
        rule = rule.name,
        severity = rule.severity,
        action = rule.action,
        matches = matches,
        threshold = rule.threshold
      })
    end
  end

  return triggered_rules
end

function M.get_recent_signals(count)
  count = count or 10
  local result = {}
  local start = math.max(1, #signals - count + 1)

  for i = start, #signals do
    table.insert(result, signals[i])
  end

  return result
end

function M.clear_signals()
  signals = {}
end

return M