local function run_test(path)
  local ok, err = pcall(dofile, path)
  if not ok then
    print('FAIL: '..path..' -> '..tostring(err))
    return false
  end
  print('PASS: '..path)
  return true
end

local failures = 0
if not run_test('nvim/tests/test_gen.lua') then failures = failures + 1 end
if not run_test('nvim/tests/test_edit.lua') then failures = failures + 1 end

if failures > 0 then
  os.exit(1)
else
  os.exit(0)
end


