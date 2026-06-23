local vim = vim

if vim.loader then
  vim.loader.enable()
end

local function prepend_path(path)
  local current_path = vim.env.PATH or ''
  for entry in current_path:gmatch('[^:]+') do
    if entry == path then
      return
    end
  end
  vim.env.PATH = path .. (current_path == '' and '' or ':' .. current_path)
end

local local_bin = vim.fs.normalize(vim.fn.expand('~/.local/bin'))
if vim.uv.fs_stat(local_bin) then
  prepend_path(local_bin)
end

-- Disable unused providers
vim.g.loaded_ruby_provider = 0
vim.g.loaded_perl_provider = 0
vim.g.loaded_node_provider = 0
vim.g.loaded_python3_provider = 0

-- Golang additional settings
-- Rely on nvim-treesitter for syntax highlighting and nvim-lspconfig for formatting.
vim.g.go_auto_sameids = 0
vim.g.go_def_mapping_enabled = 0
vim.g.go_gopls_enabled = 0
vim.g.go_gopls_gofumpt = 0

vim.filetype.add({
  extension = {
    bazelrc = 'bazelrc',
    bxl = 'bzl',
    gotmpl = 'gotmpl',
    tmpl = 'gotmpl',
  },
  filename = {
    BUCK = 'bzl',
    ['BUCK.v2'] = 'bzl',
    PACKAGE = 'bzl',
    TARGETS = 'bzl',
  },
})

-- >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Airline >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
-- Doc: https://github.com/vim-airline/vim-airline
-- Need to set before loading the plugin

-- Using vim.pack to manage plugins
vim.g.airline_extensions = { 'tabline', 'nvimlsp' }

-- Enable Tab on top
vim.g.airline_extensions_tabline_enabled = 1
vim.g.airline_extensions_tabline_buffer_idx_mode = 1

-- LSP
vim.g.airline_extensions_nvimlsp_enabled = 1

-- >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Plugins >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
local neotest_bazel_dir = vim.fs.normalize(vim.fn.expand('~/work/misc/neotest-bazel'))
local neotest_bazel_src = vim.uv.fs_stat(neotest_bazel_dir) and neotest_bazel_dir or 'https://github.com/sluongng/neotest-bazel'

local pack_specs = {
  -- Utilities
  fileline = 'https://github.com/lewis6991/fileline.nvim',
  fzf_lua = 'https://github.com/ibhagwan/fzf-lua',
  nvim_web_devicons = 'https://github.com/nvim-tree/nvim-web-devicons',
  vim_peekaboo = 'https://github.com/junegunn/vim-peekaboo',
  vim_fugitive = 'https://github.com/tpope/vim-fugitive',
  vim_surround = 'https://github.com/tpope/vim-surround',
  vim_repeat = 'https://github.com/tpope/vim-repeat',

  -- Indentation
  indent_blankline = 'https://github.com/lukas-reineke/indent-blankline.nvim',

  -- Status bar
  vim_airline = 'https://github.com/vim-airline/vim-airline',
  vim_gitgutter = 'https://github.com/airblade/vim-gitgutter',

  -- TreeSitter
  nvim_treesitter = 'https://github.com/nvim-treesitter/nvim-treesitter',
  playground = 'https://github.com/nvim-treesitter/playground',

  -- LSP Client
  cmp_buffer = 'https://github.com/hrsh7th/cmp-buffer',
  cmp_nvim_lsp = 'https://github.com/hrsh7th/cmp-nvim-lsp',
  cmp_path = 'https://github.com/hrsh7th/cmp-path',
  nvim_cmp = 'https://github.com/hrsh7th/nvim-cmp',
  nvim_lspconfig = 'https://github.com/neovim/nvim-lspconfig',
  nvim_metals = 'https://github.com/scalameta/nvim-metals',

  -- Sneak
  vim_sneak = 'https://github.com/justinmk/vim-sneak',

  -- Copilot
  copilot = 'https://github.com/github/copilot.vim',

  -- Golang
  vim_go = 'https://github.com/fatih/vim-go',

  -- Neotest
  plenary = 'https://github.com/nvim-lua/plenary.nvim',
  nvim_nio = 'https://github.com/nvim-neotest/nvim-nio',
  neotest = 'https://github.com/nvim-neotest/neotest',
  neotest_bazel = neotest_bazel_src,

  -- Coloring
  onedark = 'https://github.com/joshdick/onedark.vim',
  vim_helm = 'https://github.com/towolf/vim-helm',
}

local loaded_pack_groups = {}

local function pack_add_specs(names)
  local specs = {}
  for _, name in ipairs(names) do
    local spec = assert(pack_specs[name], name)
    table.insert(specs, spec)
  end

  vim.pack.add(specs, { confirm = false })
end

local function pack_add_once(group, names)
  if loaded_pack_groups[group] then
    return
  end

  pack_add_specs(names)
  loaded_pack_groups[group] = true
end

pack_add_specs({
  'fileline',
  'vim_peekaboo',
  'vim_fugitive',
  'vim_surround',
  'vim_repeat',
  'indent_blankline',
  'vim_airline',
  'vim_gitgutter',
  'cmp_nvim_lsp',
  'nvim_lspconfig',
  'nvim_metals',
  'vim_sneak',
  'copilot',
  'onedark',
  'vim_helm',
})

-- Neovim 0.12+ can pass a list of nodes for query captures, but the archived
-- nvim-treesitter master branch pinned in this config still assumes a single
-- TSNode for its custom predicates/directives.
if vim.fn.has('nvim-0.12') == 1 then
  local ok, query = pcall(require, 'vim.treesitter.query')
  if ok then
    local html_script_type_languages = {
      ["importmap"] = "json",
      ["module"] = "javascript",
      ["application/ecmascript"] = "javascript",
      ["text/ecmascript"] = "javascript",
    }
    local non_filetype_match_injection_language_aliases = {
      ex = "elixir",
      pl = "perl",
      sh = "bash",
      uxn = "uxntal",
      ts = "typescript",
    }
    local opts = { force = true, all = false }

    local function normalize_tsnode(node)
      if type(node) ~= "table" or node.range ~= nil then
        return node
      end

      local first = rawget(node, 1)
      if first == nil then
        return node
      end

      if pcall(function()
        return first:range(true)
      end) then
        return first
      end

      return node
    end

    local original_get_range = vim.treesitter.get_range
    vim.treesitter.get_range = function(node, source, metadata)
      return original_get_range(normalize_tsnode(node), source, metadata)
    end

    local original_get_node_text = vim.treesitter.get_node_text
    vim.treesitter.get_node_text = function(node, source, opts)
      return original_get_node_text(normalize_tsnode(node), source, opts)
    end

    local function capture_node(match, id)
      return normalize_tsnode(match[id])
    end

    local function get_parser_from_markdown_info_string(injection_alias)
      local match = vim.filetype.match({ filename = "a." .. injection_alias })
      return match or non_filetype_match_injection_language_aliases[injection_alias] or injection_alias
    end

    local function valid_args(name, pred, count, strict_count)
      local arg_count = #pred - 1
      if strict_count then
        return arg_count == count
      end
      return arg_count >= count
    end

    query.add_predicate("nth?", function(match, _pattern, _bufnr, pred)
      if not valid_args("nth?", pred, 2, true) then
        return
      end

      local node = capture_node(match, pred[2])
      local n = tonumber(pred[3])
      if node and n and node:parent() and node:parent():named_child_count() > n then
        return node:parent():named_child(n) == node
      end

      return false
    end, opts)

    query.add_predicate("is?", function(match, _pattern, bufnr, pred)
      if not valid_args("is?", pred, 2) then
        return
      end

      local locals = require('nvim-treesitter.locals')
      local node = capture_node(match, pred[2])
      local types = { unpack(pred, 3) }

      if not node then
        return true
      end

      local _, _, kind = locals.find_definition(node, bufnr)
      return vim.tbl_contains(types, kind)
    end, opts)

    query.add_predicate("kind-eq?", function(match, _pattern, _bufnr, pred)
      if not valid_args(pred[1], pred, 2) then
        return
      end

      local node = capture_node(match, pred[2])
      local types = { unpack(pred, 3) }

      if not node then
        return true
      end

      return vim.tbl_contains(types, node:type())
    end, opts)

    query.add_directive("set-lang-from-mimetype!", function(match, _, bufnr, pred, metadata)
      local node = capture_node(match, pred[2])
      if not node then
        return
      end

      local type_attr_value = vim.treesitter.get_node_text(node, bufnr)
      local configured = html_script_type_languages[type_attr_value]
      if configured then
        metadata["injection.language"] = configured
      else
        local parts = vim.split(type_attr_value, "/", {})
        metadata["injection.language"] = parts[#parts]
      end
    end, opts)

    query.add_directive("set-lang-from-info-string!", function(match, _, bufnr, pred, metadata)
      local node = capture_node(match, pred[2])
      if not node then
        return
      end

      local injection_alias = vim.treesitter.get_node_text(node, bufnr):lower()
      metadata["injection.language"] = get_parser_from_markdown_info_string(injection_alias)
    end, opts)

    query.add_directive("make-range!", function() end, opts)

    query.add_directive("downcase!", function(match, _, bufnr, pred, metadata)
      local id = pred[2]
      local node = capture_node(match, id)
      if not node then
        return
      end

      local text = vim.treesitter.get_node_text(node, bufnr, { metadata = metadata[id] }) or ""
      if not metadata[id] then
        metadata[id] = {}
      end
      metadata[id].text = string.lower(text)
    end, opts)
  end
end

-- >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Editor Settings >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

-- Set options
vim.opt.ruler = true
vim.opt.cmdheight = 2
vim.opt.history = 9000
vim.opt.signcolumn = "auto"
vim.opt.number = true
vim.opt.relativenumber = true
vim.opt.clipboard:append("unnamedplus")
vim.opt.scrolloff = 5
-- Faster CursorHold events etc.
vim.opt.updatetime = 300

if vim.fn.has('macunix') == 0 and vim.fn.has('unix') == 1 then
  local clipboard = nil

  if vim.fn.executable('wl-copy') == 1 and vim.fn.executable('wl-paste') == 1 then
    clipboard = {
      name = 'wl-clipboard',
      copy = {
        ['+'] = 'wl-copy --foreground',
        ['*'] = 'wl-copy --foreground --primary',
      },
      paste = {
        ['+'] = 'wl-paste --no-newline',
        ['*'] = 'wl-paste --no-newline --primary',
      },
      cache_enabled = 1,
    }
  elseif vim.fn.executable('xclip') == 1 then
    clipboard = {
      name = 'xclip',
      copy = {
        ['+'] = 'xclip -selection clipboard',
        ['*'] = 'xclip -selection primary',
      },
      paste = {
        ['+'] = 'xclip -selection clipboard -o',
        ['*'] = 'xclip -selection primary -o',
      },
      cache_enabled = 1,
    }
  elseif vim.fn.executable('xsel') == 1 then
    clipboard = {
      name = 'xsel',
      copy = {
        ['+'] = 'xsel -ib',
        ['*'] = 'xsel -ip',
      },
      paste = {
        ['+'] = 'xsel -ob',
        ['*'] = 'xsel -op',
      },
      cache_enabled = 1,
    }
  end

  vim.g.clipboard = clipboard
end

-- Mouse support
vim.opt.mouse = "a"

-- Show invisible characters
vim.opt.list = true
vim.opt.listchars = { tab = '»·', nbsp = '+', trail = '·', extends = '→', precedes = '←' }

-- Highlight search results and map shortcuts to clear search highlighting
vim.opt.hlsearch = true
vim.api.nvim_set_keymap('n', '<Esc><Esc>', ':nohlsearch<CR>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', '<C-l>', ':nohl<CR><C-l>', { noremap = true, silent = true })

-- Tab as spaces
vim.opt.expandtab = true
vim.opt.shiftwidth = 2
vim.opt.tabstop = 2

-- No bell on error, don't use swapfile
vim.opt.errorbells = false
vim.opt.visualbell = false

-- Indentation
vim.opt.autoindent = true
vim.opt.smartindent = true

-- Search default
vim.opt.ignorecase = true
vim.opt.smartcase = true

-- Shortcuts
-- vim.g.mapleader = ";"

-- Fast way to escape
local map, default_opts = vim.keymap.set, { noremap = true, silent = true }

local function with_bufnr(opts, bufnr)
  local merged = vim.tbl_extend('force', {}, opts or {})
  local key = vim.fn.has('nvim-0.13') == 1 and 'buf' or 'buffer'
  merged[key] = bufnr
  return merged
end

local function try_del_keymap(modes, lhs, opts)
  pcall(vim.keymap.del, modes, lhs, opts)
end

-- Fast way to escape
map('i', 'jj', '<Esc>', default_opts)

-- Pack management commands

--[[
PackUpdate user command

Implements convenient wrappers around vim.pack.update() as described in
  :h vim.pack.update()

  :PackUpdate                 Update all plugins (shows confirmation buffer)
  :PackUpdate!                Update all plugins and apply changes immediately
  :PackUpdate {name ...}      Update only the specified plugins (space-separated list)
  :PackUpdate! {name ...}     Same as above but apply immediately (force)

It also provides completion for plugin names managed by vim.pack.

PackDel user command

  :PackDel {name ...}      Remove the given plugins from disk

Provides the same name-completion.
]]

local function pack_plugin_name_complete(arg_lead, _cmd_line, _)
  -- Return list of plugin names that start with arg_lead for shell-like completion.
  local plugins = {}

  for _, plugin in ipairs(vim.pack.get()) do
    if plugin.spec then
      local name = plugin.spec.name
      if not name and plugin.spec.src then
        name = plugin.spec.src:match("/?([^/]+)$")
        if name then
          name = name:gsub("%.git$", "")
        end
      end
      if name and name:sub(1, #arg_lead) == arg_lead then
        table.insert(plugins, name)
      end
    end
  end
  table.sort(plugins)
  return plugins
end
vim.api.nvim_create_user_command('PackUpdate', function(opts)
  local names
  if opts.args ~= '' then
    -- Split args by whitespace.
    names = {}
    for name in string.gmatch(opts.args, "%S+") do
      table.insert(names, name)
    end
  end

  vim.pack.update(names, { force = opts.bang })
end, {
  bang = true,
  nargs = '*',
  complete = pack_plugin_name_complete,
})
vim.api.nvim_create_user_command('PackDel', function(opts)
  if opts.args == '' then
    vim.notify('PackDel: at least one plugin name must be supplied', vim.log.levels.ERROR)
    return
  end

  local names = {}
  for name in string.gmatch(opts.args, '%S+') do
    table.insert(names, name)
  end

  vim.pack.del(names)
end, {
  nargs = '+',
  complete = pack_plugin_name_complete,
})

-- Split window behavior
vim.opt.splitbelow = true
vim.opt.splitright = true

-- Don't use Ex mode
vim.api.nvim_set_keymap('n', 'Q', '<Nop>', { noremap = true, silent = true })

-- Color and autocmd for color scheme
vim.opt.termguicolors = true
vim.cmd.colorscheme('onedark')

-- Make inlay hints slightly brighter than comment grey
vim.api.nvim_set_hl(0, 'LspInlayHint', { fg = '#ABB2BF' })

-- >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> LSP Config >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
-- Remove builtin LSP keymaps so only the custom mappings below remain.
try_del_keymap("n", "grn")
try_del_keymap("n", "grr")
try_del_keymap({ "v", "n" }, "gra")
try_del_keymap("n", "grx")

local function on_list(options)
  vim.fn.setqflist({}, ' ', options)
  if #options.items > 1 then
    vim.cmd("botright cwindow") -- always take full width
  end
  vim.cmd.cfirst()
end

local function diagnostic_jump_open_float(diagnostic, bufnr)
  if not diagnostic then
    return
  end

  vim.diagnostic.open_float(bufnr, {
    border = 'rounded',
    focus = false,
    scope = 'cursor',
  })
end

local function flatten_lsp_locations(result)
  if not result then
    return {}
  end

  if result.uri or result.targetUri then
    return { result }
  end

  return result
end

local function location_decl_range(path, symbol)
  local ok, lines = pcall(vim.fn.readfile, path)
  if not ok then
    return {
      start = { line = 0, character = 0 },
      ['end'] = { line = 0, character = 0 },
    }
  end

  local escaped = vim.pesc(symbol)
  local patterns = {
    '@interface%s+' .. escaped .. '%f[%W]',
    'class%s+' .. escaped .. '%f[%W]',
    'interface%s+' .. escaped .. '%f[%W]',
    'enum%s+' .. escaped .. '%f[%W]',
    'record%s+' .. escaped .. '%f[%W]',
  }

  for index, line in ipairs(lines) do
    for _, pattern in ipairs(patterns) do
      if line:find(pattern) then
        local start_col = line:find(symbol, 1, true) - 1
        return {
          start = { line = index - 1, character = start_col },
          ['end'] = { line = index - 1, character = start_col + #symbol },
        }
      end
    end
  end

  return {
    start = { line = 0, character = 0 },
    ['end'] = { line = 0, character = 0 },
  }
end

local function jdk_src_zip_candidates()
  local candidates = {}
  for _, home in ipairs({
    vim.env.METALS_JAVA_HOME,
    vim.env.JAVA_HOME,
  }) do
    if home and home ~= '' then
      table.insert(candidates, home)
    end
  end

  local sysname = vim.uv.os_uname().sysname
  if sysname == 'Linux' then
    vim.list_extend(candidates, {
      '/usr/lib/jvm/java-25-graalvm-ce',
      '/usr/lib/jvm/java-25-openjdk',
      '/usr/lib/jvm/java-21-openjdk',
      '/usr/lib/jvm/java-17-openjdk',
      '/usr/lib/jvm/default',
    })
  elseif sysname == 'Darwin' then
    vim.list_extend(candidates, {
      '/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home',
      '/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home',
    })
  end

  local seen = {}
  local src_zips = {}
  for _, home in ipairs(candidates) do
    if not seen[home] then
      seen[home] = true
      local src_zip = vim.fs.joinpath(home, 'lib', 'src.zip')
      if vim.fn.filereadable(src_zip) == 1 then
        table.insert(src_zips, src_zip)
      end
    end
  end

  return src_zips
end

local function first_jdk_src_entry(src_zip, relative_path)
  if vim.fn.executable('unzip') ~= 1 then
    return nil
  end

  local result = vim.system({ 'unzip', '-Z', '-1', src_zip, '*/' .. relative_path }, { text = true }):wait()
  if result.code ~= 0 or not result.stdout or result.stdout == '' then
    return nil
  end

  return result.stdout:match('[^\r\n]+')
end

local function extract_jdk_source(workspace, relative_path)
  local output = vim.fs.joinpath(workspace, '.metals', 'readonly', 'dependencies', 'jdk-src', relative_path)
  if vim.fn.filereadable(output) == 1 then
    return output
  end

  for _, src_zip in ipairs(jdk_src_zip_candidates()) do
    local entry = first_jdk_src_entry(src_zip, relative_path)
    if entry then
      local result = vim.system({ 'unzip', '-p', src_zip, entry }, { text = true }):wait()
      if result.code == 0 and result.stdout and result.stdout ~= '' then
        vim.fn.mkdir(vim.fn.fnamemodify(output, ':h'), 'p')
        local lines = vim.split(result.stdout, '\n', { plain = true })
        if lines[#lines] == '' then
          table.remove(lines)
        end
        vim.fn.writefile(lines, output)
        return output
      end
    end
  end

  return nil
end

local function metals_workspace_for_buffer(bufnr)
  local buffer_name = vim.api.nvim_buf_get_name(bufnr)
  local start_path = buffer_name ~= '' and vim.fn.fnamemodify(buffer_name, ':p:h') or vim.fn.getcwd()
  local marker = vim.fs.find('.metals', { upward = true, path = start_path, type = 'directory' })[1]
  if not marker then
    return nil
  end

  return vim.fs.dirname(marker)
end

local function java_source_root_from_buffer(bufnr)
  local buffer_name = vim.api.nvim_buf_get_name(bufnr)
  if buffer_name == '' or not buffer_name:match('%.java$') then
    return nil
  end

  local package
  for _, line in ipairs(vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)) do
    package = line:match('^%s*package%s+([%w_%.]+)%s*;%s*$')
    if package then
      break
    end
  end

  if not package then
    return nil
  end

  local package_path = package:gsub('%.', '/')
  local absolute = vim.fn.fnamemodify(buffer_name, ':p')
  local suffix = '/' .. package_path .. '/' .. vim.fn.fnamemodify(buffer_name, ':t')
  if absolute:sub(-#suffix) ~= suffix then
    return nil
  end

  return absolute:sub(1, #absolute - #suffix)
end

local function workspace_java_source_path(workspace, relative_path, bufnr)
  local roots = {}
  local seen = {}

  local function add_root(root)
    if not root or root == '' or seen[root] then
      return
    end
    seen[root] = true
    table.insert(roots, root)
  end

  add_root(java_source_root_from_buffer(bufnr))

  for _, root in ipairs({
    'src/main/java',
    'src/test/java',
    'src/java_tools/buildjar/java',
    'src/java_tools/junitrunner/java',
    'src/tools/android/java',
    'tools/java/runfiles',
  }) do
    add_root(vim.fs.joinpath(workspace, root))
  end

  add_root(workspace)

  for _, root in ipairs(roots) do
    local path = vim.fs.joinpath(root, relative_path)
    if vim.fn.filereadable(path) == 1 then
      return path
    end
  end

  return nil
end

local function split_dotted_name(name)
  local parts = {}
  for part in name:gmatch('[^%.]+') do
    table.insert(parts, part)
  end
  return parts
end

local function join_parts(parts, start_index, end_index, separator)
  local selected = {}
  for index = start_index, end_index do
    table.insert(selected, parts[index])
  end
  return table.concat(selected, separator)
end

local function java_import_relative_paths(import)
  local parts = split_dotted_name(import)
  local paths = {}
  local seen = {}

  local function add_path(end_index)
    if end_index < 1 then
      return
    end

    local relative_path = join_parts(parts, 1, end_index, '/') .. '.java'
    if not seen[relative_path] then
      seen[relative_path] = true
      table.insert(paths, relative_path)
    end
  end

  add_path(#parts)
  for end_index = #parts - 1, 1, -1 do
    add_path(end_index)
  end

  return paths
end

local proto_files_cache = {}
local proto_java_outer_cache = {}

local function upper_camel_from_proto_basename(name)
  local words = {}
  for word in name:gmatch('[A-Za-z0-9]+') do
    table.insert(words, word:sub(1, 1):upper() .. word:sub(2))
  end

  return table.concat(words, '')
end

local function proto_java_package(lines)
  for _, line in ipairs(lines) do
    local package = line:match('^%s*option%s+java_package%s*=%s*"([^"]+)"%s*;%s*$')
    if package then
      return package
    end
  end

  return nil
end

local function proto_outer_class_name(path, lines)
  for _, line in ipairs(lines) do
    local outer = line:match('^%s*option%s+java_outer_classname%s*=%s*"([^"]+)"%s*;%s*$')
    if outer then
      return outer
    end
  end

  return upper_camel_from_proto_basename(vim.fn.fnamemodify(path, ':t:r'))
end

local function workspace_proto_files(workspace)
  if proto_files_cache[workspace] then
    return proto_files_cache[workspace]
  end

  local files = {}
  if vim.fn.executable('rg') == 1 then
    local result = vim.system({
      'rg',
      '--files',
      '--glob',
      '*.proto',
      '--glob',
      '!bazel-*',
      '--glob',
      '!.metals/**',
      '--glob',
      '!.bazelbsp/**',
    }, { cwd = workspace, text = true }):wait()
    if result.code == 0 and result.stdout then
      for line in result.stdout:gmatch('[^\r\n]+') do
        table.insert(files, vim.fs.joinpath(workspace, line))
      end
    end
  end

  if #files == 0 then
    files = vim.fn.globpath(workspace, 'src/**/*.proto', false, true)
  end

  proto_files_cache[workspace] = files
  return files
end

local function proto_for_java_outer(workspace, package_name, outer_class)
  local cache_key = workspace .. '\0' .. package_name .. '\0' .. outer_class
  if proto_java_outer_cache[cache_key] ~= nil then
    return proto_java_outer_cache[cache_key] or nil
  end

  for _, path in ipairs(workspace_proto_files(workspace)) do
    local ok, lines = pcall(vim.fn.readfile, path)
    if ok and proto_java_package(lines) == package_name and proto_outer_class_name(path, lines) == outer_class then
      proto_java_outer_cache[cache_key] = path
      return path
    end
  end

  proto_java_outer_cache[cache_key] = false
  return nil
end

local function proto_block_end(lines, start_line, limit)
  local depth = 0
  local saw_open = false
  for index = start_line, limit do
    local line = lines[index]
    local _, opens = line:gsub('{', '')
    local _, closes = line:gsub('}', '')
    if opens > 0 then
      saw_open = true
    end
    depth = depth + opens - closes
    if saw_open and depth <= 0 then
      return index
    end
  end

  return limit
end

local function proto_decl_range(path, nested_names)
  local ok, lines = pcall(vim.fn.readfile, path)
  if not ok then
    return {
      start = { line = 0, character = 0 },
      ['end'] = { line = 0, character = 0 },
    }
  end

  local search_start = 1
  local search_end = #lines
  local found_line = 1
  local found_col = 0

  for _, name in ipairs(nested_names) do
    local escaped = vim.pesc(name)
    local match_line
    for index = search_start, search_end do
      local line = lines[index]
      if line:find('^%s*message%s+' .. escaped .. '%f[%W]') or line:find('^%s*enum%s+' .. escaped .. '%f[%W]') then
        match_line = index
        break
      end
    end

    if not match_line then
      break
    end

    found_line = match_line
    found_col = (lines[match_line]:find(name, 1, true) or 1) - 1
    search_start = match_line + 1
    search_end = proto_block_end(lines, match_line, search_end) - 1
  end

  return {
    start = { line = found_line - 1, character = found_col },
    ['end'] = { line = found_line - 1, character = found_col + #nested_names[#nested_names] },
  }
end

local function generated_proto_definition(workspace, import)
  local parts = split_dotted_name(import)
  if #parts < 2 then
    return nil
  end

  for outer_index = #parts - 1, 2, -1 do
    local package_name = join_parts(parts, 1, outer_index - 1, '.')
    local outer_class = parts[outer_index]
    local proto_path = proto_for_java_outer(workspace, package_name, outer_class)
    if proto_path then
      local nested_names = {}
      for index = outer_index + 1, #parts do
        table.insert(nested_names, parts[index])
      end
      if #nested_names == 0 then
        return nil
      end

      return {
        uri = vim.uri_from_fname(proto_path),
        range = proto_decl_range(proto_path, nested_names),
      }
    end
  end

  return nil
end

local function java_import_definition_at_cursor(bufnr)
  local row = vim.api.nvim_win_get_cursor(0)[1]
  local line = vim.api.nvim_buf_get_lines(bufnr, row - 1, row, false)[1] or ''
  local import = line:match('^%s*import%s+([%w_%.]+)%s*;%s*$')
  if not import then
    return nil
  end

  local workspace = metals_workspace_for_buffer(bufnr)
  if not workspace then
    return nil
  end

  local symbol = import:match('([^.]+)$')
  local relative_path = import:gsub('%.', '/') .. '.java'
  if import:match('^java%.') then
    local jdk_source = extract_jdk_source(workspace, relative_path)
    if jdk_source then
      return {
        uri = vim.uri_from_fname(jdk_source),
        range = location_decl_range(jdk_source, symbol),
      }
    end
  end

  for _, candidate in ipairs(java_import_relative_paths(import)) do
    local workspace_source = workspace_java_source_path(workspace, candidate, bufnr)
    if workspace_source then
      return {
        uri = vim.uri_from_fname(workspace_source),
        range = location_decl_range(workspace_source, symbol),
      }
    end
  end

  local dependency_root = vim.fs.joinpath(workspace, '.metals', 'readonly', 'dependencies')
  local matches = vim.fn.globpath(dependency_root, '*/' .. relative_path, false, true)
  if #matches > 0 then
    table.sort(matches)
    local path = matches[1]
    return {
      uri = vim.uri_from_fname(path),
      range = location_decl_range(path, symbol),
    }
  end

  return generated_proto_definition(workspace, import)
end

local function show_definition_locations(locations, opts)
  if opts and opts.on_list then
    opts.on_list({
      title = 'LSP definitions',
      items = vim.lsp.util.locations_to_items(locations, 'utf-16'),
    })
    return
  end

  if #locations == 1 then
    vim.lsp.util.show_document(locations[1], 'utf-16', { focus = true })
    return
  end

  vim.fn.setqflist({}, ' ', {
    title = 'LSP definitions',
    items = vim.lsp.util.locations_to_items(locations, 'utf-16'),
  })
  vim.cmd('botright cwindow')
end

local function lsp_definition_with_java_import_fallback(opts)
  local bufnr = vim.api.nvim_get_current_buf()
  local fallback = java_import_definition_at_cursor(bufnr)
  if fallback then
    show_definition_locations({ fallback }, opts)
    return
  end

  local params = vim.lsp.util.make_position_params(0, 'utf-16')

  vim.lsp.buf_request_all(bufnr, 'textDocument/definition', params, function(responses)
    local locations = {}
    for _, response in pairs(responses or {}) do
      if response.result then
        for _, location in ipairs(flatten_lsp_locations(response.result)) do
          table.insert(locations, location)
        end
      end
    end

    if #locations > 0 then
      show_definition_locations(locations, opts)
      return
    end

    vim.notify('No definition found', vim.log.levels.INFO)
  end)
end

local function java_reference_symbol_at_cursor(bufnr)
  local row = vim.api.nvim_win_get_cursor(0)[1]
  local line = vim.api.nvim_buf_get_lines(bufnr, row - 1, row, false)[1] or ''
  local import = line:match('^%s*import%s+([%w_%.]+)%s*;%s*$')
  if import then
    return import:match('([^.]+)$')
  end

  local symbol = vim.fn.expand('<cword>')
  if symbol:match('^[A-Z][%w_]*$') then
    return symbol
  end

  return nil
end

local function java_reference_search_roots(workspace, bufnr)
  local roots = {}
  local seen = {}

  local function add_root(root)
    if not root or root == '' or seen[root] or vim.fn.isdirectory(root) ~= 1 then
      return
    end
    seen[root] = true
    table.insert(roots, root)
  end

  add_root(java_source_root_from_buffer(bufnr))

  for _, root in ipairs({
    'src/main/java',
    'src/test/java',
    'src/java_tools/buildjar/java',
    'src/java_tools/junitrunner/java',
    'src/tools/android/java',
    'tools/java/runfiles',
  }) do
    add_root(vim.fs.joinpath(workspace, root))
  end

  if #roots == 0 then
    add_root(workspace)
  end

  return roots
end

local function java_references_from_rg(symbol, workspace, bufnr, opts)
  if vim.fn.executable('rg') ~= 1 then
    return false
  end

  local roots = java_reference_search_roots(workspace, bufnr)
  if #roots == 0 then
    return false
  end

  local args = {
    'rg',
    '--no-heading',
    '--color',
    'never',
    '-n',
    '--column',
    '--glob',
    '*.java',
    '\\b' .. symbol .. '\\b',
  }

  for _, root in ipairs(roots) do
    table.insert(args, root)
  end

  local result = vim.system(args, { text = true }):wait()
  if result.code ~= 0 or not result.stdout or result.stdout == '' then
    return false
  end

  local items = {}
  for line in result.stdout:gmatch('[^\r\n]+') do
    local filename, lnum, col, text = line:match('^([^:]+):(%d+):(%d+):(.*)$')
    if filename then
      table.insert(items, {
        filename = filename,
        lnum = tonumber(lnum),
        col = tonumber(col),
        text = text,
      })
    end
  end

  if #items == 0 then
    return false
  end

  local list = {
    title = 'Java references for ' .. symbol,
    items = items,
  }
  if opts and opts.on_list then
    opts.on_list(list)
  else
    vim.fn.setqflist({}, ' ', list)
    vim.cmd('botright cwindow')
  end

  return true
end

local function lsp_references_with_java_fallback(opts)
  local bufnr = vim.api.nvim_get_current_buf()
  if vim.bo[bufnr].filetype == 'java' then
    local symbol = java_reference_symbol_at_cursor(bufnr)
    local workspace = metals_workspace_for_buffer(bufnr)
    if symbol and workspace and java_references_from_rg(symbol, workspace, bufnr, opts) then
      return
    end
  end

  vim.lsp.buf.references(nil, opts)
end



-- Configure diagnostics globally
vim.diagnostic.config({
  virtual_text = true,
  signs = true,
  update_in_insert = false,
  float = {
    border = 'rounded',
    source = 'if_many',
    header = '',
    prefix = '',
  },
})

-- Autocmd for LSP client attachment
vim.api.nvim_create_autocmd('LspAttach', {
  group = vim.api.nvim_create_augroup('my.lsp.attach', { clear = true }), -- Clear previous autocmds for this group
  callback = function(args)
    local bufnr = args.buf
    local opts = with_bufnr({ remap = false }, bufnr)
    local client = vim.lsp.get_client_by_id(args.data.client_id)
    if not client then
      vim.notify("lsp client id " .. args.data.client_id .. " not found.", vim.log.levels.WARN)
      return -- Stop
    end

    -- Set buffer-local options
    vim.bo[bufnr].omnifunc = 'v:lua.vim.lsp.omnifunc'
    vim.bo[bufnr].tagfunc = 'v:lua.vim.lsp.tagfunc'
    vim.bo[bufnr].formatexpr = 'v:lua.vim.lsp.formatexpr()'

    if client:supports_method('textDocument/inlayHint') then
      vim.lsp.inlay_hint.enable(true, { bufnr = bufnr })
    end

    if client:supports_method('textDocument/rename') then
      vim.keymap.set("n", "<Leader>rn", function() vim.lsp.buf.rename() end, opts)
    end
    if client:supports_method('textDocument/codeAction') then
      vim.keymap.set("n", "<Leader>ca", function() vim.lsp.buf.code_action() end, opts)
    end
    if client:supports_method('textDocument/formatting') then
      -- Non-blocking manual trigger
      vim.keymap.set(
        "n",
        "<Leader>cf",
        function() vim.lsp.buf.format({ async = true }) end,
        opts
      )

      -- Format-on-save ------------------------------
      -- NOTE: Clearing the same augroup on every LspAttach was causing the
      -- autocmd to be registered only for the last attached buffer.  Instead
      -- we create a _single_ augroup once, and just append buffer-local
      -- autocmds to it.  This guarantees each buffer keeps its own listener
      -- without interfering with others.
      local fmt_group = vim.api.nvim_create_augroup('my_lsp_format', { clear = false })

      -- Ensure we don't create duplicate autocmds for the same buffer.
      vim.api.nvim_clear_autocmds({ group = fmt_group, buffer = bufnr })

      vim.api.nvim_create_autocmd('BufWritePre', {
        group = fmt_group,
        buffer = bufnr,
        callback = function()
          if not client.server_capabilities.documentFormattingProvider then
            return
          end
          vim.lsp.buf.format({ bufnr = bufnr })
        end,
      })
    end
    if client:supports_method('textDocument/references') then
      vim.keymap.set("n", "gr", function() lsp_references_with_java_fallback({ on_list = on_list }) end, opts)
      vim.keymap.set("n", "gR", function()
        vim.cmd.vsplit()
        lsp_references_with_java_fallback({ on_list = on_list })
      end, opts)
    end
    if client:supports_method('textDocument/definition') then
      vim.keymap.set("n", "gd", function() lsp_definition_with_java_import_fallback({ on_list = on_list }) end, opts)
      vim.keymap.set("n", "gD", function()
        vim.cmd.vsplit()
        lsp_definition_with_java_import_fallback({ on_list = on_list })
      end, opts)
    end
    vim.keymap.set('n', '<leader>e', vim.diagnostic.open_float, opts)
    vim.keymap.set('n', '<leader>E', vim.diagnostic.setloclist, opts)
    vim.keymap.set('n', ']d', function()
      vim.diagnostic.jump({ count = 1, on_jump = diagnostic_jump_open_float })
    end, opts)
    vim.keymap.set('n', '[d', function() -- Add jump to previous diagnostic
      vim.diagnostic.jump({ count = -1, on_jump = diagnostic_jump_open_float })
    end, opts)

    if client:supports_method('textDocument/hover') then
      vim.keymap.set("n", "K", vim.lsp.buf.hover, opts)
    end
    if client:supports_method('textDocument/implementation') then
      vim.keymap.set("n", "gi", vim.lsp.buf.implementation, opts)
    end
    if client:supports_method('textDocument/typeDefinition') then
      vim.keymap.set("n", "<leader>D", vim.lsp.buf.type_definition, opts)
    end
    if client:supports_method('textDocument/declaration') then
      vim.keymap.set("n", "<leader>vd", vim.lsp.buf.declaration, opts)
    end
    if client:supports_method('textDocument/signatureHelp') then
      vim.keymap.set("i", "<C-s>", vim.lsp.buf.signature_help, opts) -- For signature help in insert mode
    end
    if client:supports_method('textDocument/documentHighlight') then
      local hl_group = vim.api.nvim_create_augroup('my_lsp_highlight', { clear = false })

      -- Using once-per-buffer autocmds avoids recreating them on every
      -- CursorHold for the same buffer while still providing highlight & clear
      -- Remove previous highlight autocmds for this buffer (if any) before
      -- adding new ones.
      vim.api.nvim_clear_autocmds({ group = hl_group, buffer = bufnr })

      vim.api.nvim_create_autocmd({ 'CursorHold', 'CursorHoldI' }, {
        group = hl_group,
        buffer = bufnr,
        callback = vim.lsp.buf.document_highlight,
      })
      vim.api.nvim_create_autocmd('CursorMoved', {
        group = hl_group,
        buffer = bufnr,
        callback = vim.lsp.buf.clear_references,
      })
    end
    -- if client:supports_method('textDocument/completion') then
    --   vim.lsp.completion.enable(true, client.id, bufnr, { autotrigger = true })
    -- end
  end,
})


-- LSP capabilities (nvim-cmp integration)
local lsp_capabilities = vim.lsp.protocol.make_client_capabilities()
do
  local ok, cmp_nvim_lsp = pcall(require, 'cmp_nvim_lsp')
  if ok then
    lsp_capabilities = cmp_nvim_lsp.default_capabilities(lsp_capabilities)
  end
end

do
  local function is_macos()
    return vim.uv.os_uname().sysname == 'Darwin'
  end

  local function is_linux()
    return vim.uv.os_uname().sysname == 'Linux'
  end

  local function is_windows()
    return vim.fn.has('win32') == 1 or vim.fn.has('win64') == 1
  end

  local function has_java_sources(home)
    if not home or home == '' then
      return false
    end

    local java_bin = is_windows() and 'java.exe' or 'java'
    return vim.uv.fs_stat(vim.fs.joinpath(home, 'bin', java_bin)) ~= nil and
        vim.uv.fs_stat(vim.fs.joinpath(home, 'lib', 'src.zip')) ~= nil
  end

  local function find_supported_metals_java_home()
    local candidates = {}
    for _, home in ipairs({
      vim.env.METALS_JAVA_HOME,
      vim.env.JAVA_HOME,
    }) do
      if home and home ~= '' then
        table.insert(candidates, home)
      end
    end

    if is_macos() then
      vim.list_extend(candidates, {
        '/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home',
        '/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home',
      })
    elseif is_linux() then
      vim.list_extend(candidates, {
        '/usr/lib/jvm/java-25-openjdk',
        '/usr/lib/jvm/java-21-openjdk',
        '/usr/lib/jvm/java-17-openjdk',
        '/usr/lib/jvm/default',
        '/usr/lib/jvm/java-25-graalvm-ce',
      })
    end

    for _, home in ipairs(candidates) do
      if has_java_sources(home) then
        return home
      end
    end
  end

  local ok, metals = pcall(require, 'metals')
  if not ok then
    vim.notify('nvim-metals not available; skipping Metals setup', vim.log.levels.WARN)
  else
    local metals_java_home = find_supported_metals_java_home()
    local metals_target_version = '2.0.0-M10'
    local metals_version_marker = vim.fn.stdpath('cache') .. '/nvim-metals/version.txt'
    local metals_config_lib = require('metals.config')
    local metals_install = require('metals.install')
    local metals_version_ready = false

    local function read_metals_version_marker()
      if vim.fn.filereadable(metals_version_marker) == 0 then
        return nil
      end

      local lines = vim.fn.readfile(metals_version_marker)
      return lines[1]
    end

    local function write_metals_version_marker(version)
      vim.fn.mkdir(vim.fn.fnamemodify(metals_version_marker, ':h'), 'p')
      vim.fn.writefile({ version }, metals_version_marker)
    end

    local function installed_metals_version(metals_bin)
      if vim.fn.executable(metals_bin) == 0 then
        return nil
      end

      local result = vim.system({ metals_bin, '-v' }, { text = true }):wait()
      if result.code ~= 0 or not result.stdout then
        return nil
      end

      return result.stdout:match('metals%s+([^\n]+)')
    end

    local function current_workspace_search_path()
      local buffer_name = vim.api.nvim_buf_get_name(0)
      return buffer_name ~= '' and vim.fn.fnamemodify(buffer_name, ':p:h') or vim.fn.getcwd()
    end

    local function find_workspace_marker(name, marker_type)
      return vim.fs.find(name, {
        upward = true,
        path = current_workspace_search_path(),
        type = marker_type,
      })[1]
    end

    local function bazel_bsp_config_path()
      local bsp_dir = find_workspace_marker('.bsp', 'directory')
      local config_path = bsp_dir and (bsp_dir .. '/bazelbsp.json') or nil
      if config_path and vim.fn.filereadable(config_path) == 1 then
        return config_path
      end

      return nil
    end

    local function bazel_bsp_server_name()
      local config_path = bazel_bsp_config_path()
      if not config_path then
        return nil
      end

      local ok, lines = pcall(vim.fn.readfile, config_path)
      if not ok then
        return 'bazelbsp'
      end

      local decode_ok, decoded = pcall(vim.json.decode, table.concat(lines, '\n'))
      if decode_ok and type(decoded) == 'table' and type(decoded.name) == 'string' and decoded.name ~= '' then
        return decoded.name
      end

      return 'bazelbsp'
    end

    local function is_bazel_mbt_workspace()
      return find_workspace_marker('bazel.mbt.sh', 'file') ~= nil
    end

    local function proto_java_virtual_target(uri)
      local proto_uri, class_name = uri:match('^(.*%.proto)%.metals%-proto%-java/([^/]+)%.java$')
      if not proto_uri then
        return nil
      end

      local proto_path = vim.uri_to_fname(proto_uri)
      if vim.fn.filereadable(proto_path) == 0 then
        return nil
      end

      return proto_path, class_name
    end

    local function proto_decl_range(proto_path, class_name)
      local ok, lines = pcall(vim.fn.readfile, proto_path)
      if not ok then
        return nil
      end

      local escaped = vim.pesc(class_name)
      for index, line in ipairs(lines) do
        if line:find('^%s*message%s+' .. escaped .. '%f[%W]')
            or line:find('^%s*enum%s+' .. escaped .. '%f[%W]')
            or line:find('^%s*service%s+' .. escaped .. '%f[%W]') then
          local start_col = line:find(class_name, 1, true) - 1
          return {
            start = { line = index - 1, character = start_col },
            ['end'] = { line = index - 1, character = start_col + #class_name },
          }
        end
      end

      return nil
    end

    local function rewrite_proto_java_virtual_location(location)
      local uri = location.uri or location.targetUri
      if not uri then
        return location
      end

      local proto_path, class_name = proto_java_virtual_target(uri)
      if not proto_path then
        return location
      end

      local range = proto_decl_range(proto_path, class_name)
      if not range then
        return location
      end

      local rewritten = vim.deepcopy(location)
      local proto_uri = vim.uri_from_fname(proto_path)
      if rewritten.uri then
        rewritten.uri = proto_uri
        rewritten.range = range
      end
      if rewritten.targetUri then
        rewritten.targetUri = proto_uri
        rewritten.targetRange = range
        rewritten.targetSelectionRange = range
      end
      return rewritten
    end

    local function install_proto_java_location_rewriter()
      if vim.g.my_proto_java_location_rewriter_installed then
        return
      end

      vim.g.my_proto_java_location_rewriter_installed = true
      local default_locations_to_items = vim.lsp.util.locations_to_items
      vim.lsp.util.locations_to_items = function(locations, offset_encoding)
        local rewritten = locations
        if type(locations) == 'table' then
          local is_list = vim.islist or vim.tbl_islist
          if is_list(locations) then
            rewritten = {}
            for index, location in ipairs(locations) do
              rewritten[index] = rewrite_proto_java_virtual_location(location)
            end
          else
            rewritten = rewrite_proto_java_virtual_location(locations)
          end
        end

        return default_locations_to_items(rewritten, offset_encoding)
      end
    end

    install_proto_java_location_rewriter()

    local function create_metals_config()
      local metals_config = metals.bare_config()
      local server_properties = {
        "-Xmx4g",
      }
      local bazel_bsp_server = bazel_bsp_server_name()
      local bazel_bsp_workspace = bazel_bsp_server ~= nil

      if bazel_bsp_workspace then
        table.insert(server_properties, "-Dmetals.auto-import-builds=all")
        table.insert(server_properties, "-Dmetals.preferred-build-server=" .. bazel_bsp_server)
        table.insert(server_properties, "-Dmetals.presentation-compiler-diagnostics=false")
      elseif is_bazel_mbt_workspace() then
        table.insert(server_properties, "-Dmetals.auto-import-builds=all")
        table.insert(server_properties, "-Dmetals.preferred-build-server=MBT")
        table.insert(server_properties, "-Dmetals.presentation-compiler-diagnostics=false")
      end

      if is_macos() then
        table.insert(server_properties, "-Dmetals.macos-max-watch-roots=65536")
      end

      metals_config.capabilities = lsp_capabilities
      metals_config.settings = {
        serverVersion = metals_target_version,
        serverProperties = server_properties,
      }

      if bazel_bsp_workspace then
        metals_config.settings.defaultBspToBuildTool = true
      end

      if metals_java_home then
        metals_config.settings.javaHome = metals_java_home
        metals_config.cmd_env = vim.tbl_extend('force', metals_config.cmd_env or {}, {
          JAVA_HOME = metals_java_home,
        })
      end

      return metals_config
    end

    local function ensure_target_metals_version(metals_config)
      if metals_version_ready then
        return true
      end

      local metals_bin = metals_config_lib.metals_bin()
      if vim.fn.executable(metals_bin) == 1 and read_metals_version_marker() == metals_target_version then
        metals_version_ready = true
        return true
      end

      local installed_version = installed_metals_version(metals_bin)
      if installed_version == metals_target_version then
        write_metals_version_marker(installed_version)
        metals_version_ready = true
        return true
      end

      local validated = metals_config_lib.validate_config(vim.deepcopy(metals_config), vim.api.nvim_get_current_buf())
      if not validated and vim.fn.executable(metals_bin) == 1 then
        return false
      end

      metals_install.install_or_update(true)

      installed_version = installed_metals_version(metals_bin)
      if installed_version == metals_target_version then
        write_metals_version_marker(installed_version)
        metals_version_ready = true
        return true
      end

      vim.notify(
        string.format(
          'Expected Metals %s but found %s after install',
          metals_target_version,
          installed_version or 'no installed binary'
        ),
        vim.log.levels.ERROR
      )
      return false
    end

    vim.api.nvim_create_autocmd('FileType', {
      group = vim.api.nvim_create_augroup('my.metals', { clear = true }),
      pattern = { 'scala', 'sbt', 'java' },
      callback = function()
        local metals_config = create_metals_config()
        if not ensure_target_metals_version(metals_config) then
          return
        end

        if metals_java_home then
          vim.env.JAVA_HOME = metals_java_home
        end

        metals.initialize_or_attach(metals_config)
      end,
    })
  end
end

local function enable_lsp_config(name, overrides)
  overrides = vim.tbl_deep_extend('force', { capabilities = lsp_capabilities }, overrides or {})
  vim.lsp.config(name, overrides)

  local resolved = vim.lsp.config[name]
  if not resolved then
    vim.notify(string.format('Skipping %s LSP: config not found', name), vim.log.levels.INFO)
    return
  end

  local cmd = resolved.cmd
  local executable

  if type(cmd) == 'table' then
    executable = cmd[1]
  elseif type(cmd) == 'string' then
    executable = cmd
  end

  if executable and executable ~= '' and vim.fn.executable(executable) == 0 then
    vim.notify(
      string.format('Skipping %s LSP: command "%s" is not executable', name, executable),
      vim.log.levels.INFO
    )
    return
  end

  vim.lsp.enable(name)
end

local function buffer_search_path(bufnr)
  local name = vim.api.nvim_buf_get_name(bufnr)
  if name ~= '' then
    return vim.fs.dirname(name)
  end
  return vim.fn.getcwd()
end

local function starlark_root(bufnr, markers)
  local marker = vim.fs.find(markers, {
    upward = true,
    path = buffer_search_path(bufnr),
  })[1]
  return marker and vim.fs.dirname(marker) or nil
end

local bazel_starlark_markers = { 'WORKSPACE', 'WORKSPACE.bazel', 'MODULE.bazel' }
local buck2_starlark_markers = { '.buckconfig', '.buckroot' }

local function buck2_lsp_cmd(root_dir)
  if vim.fn.executable('buck2') == 1 then
    return { 'buck2', 'lsp' }
  end

  local repo_local_buck2 = vim.fs.joinpath(root_dir, 'bootstrap', 'buck2')
  if vim.fn.executable(repo_local_buck2) == 1 then
    return { repo_local_buck2, 'lsp' }
  end

  return nil
end

local function buck2_lsp_dispatchers(dispatchers)
  local original_on_error = dispatchers.on_error
  return vim.tbl_extend('force', dispatchers, {
    on_error = function(errkind, err)
      if errkind == vim.lsp.rpc.client_errors.INVALID_SERVER_MESSAGE
          and type(err) == 'table'
          and err.jsonrpc == '2.0'
          and err.id ~= nil
          and err.method == nil
          and err.result == nil
          and err.error == nil then
        return
      end

      return original_on_error(errkind, err)
    end,
  })
end

enable_lsp_config('gopls', {
  settings = {
    gopls = {
      usePlaceholders = true,
      buildFlags = { "-tags=linux,amd64" },
      -- ["local"] = "github.com/buildbuddy-io/buildbuddy",
      staticcheck = true,
      analyses = {
        SA1019 = false,
        SA1029 = false,
        ST1000 = false,
        ST1003 = false,
        ST1005 = false,
        ST1006 = false,
        ST1008 = false,
        ST1012 = false,
        ST1016 = false,
        ST1017 = false,
        ST1020 = false,
        ST1021 = false,
        ST1022 = false,
        ST1023 = false,
        QF1001 = false,
        QF1003 = false,
        QF1004 = false,
        QF1005 = false,
        QF1006 = false,
        QF1008 = false,
        QF1011 = false,
        QF1012 = false,
        U1000  = false,
      },
      directoryFilters = {
        "-**/bazel-",
        "-**/node_modules",
      },
      vulncheck = "Imports",
      semanticTokens = true,
      hints = {
        -- parameterNames = true,
        assignVariableTypes = true,
        constantValues = true,
        rangeVariableTypes = true,
        compositeLiteralTypes = true,
        compositeLiteralFields = true,
        functionTypeParameters = true,
      },
    },
  },
})

enable_lsp_config('rust_analyzer', {
  settings = {
    ["rust-analyzer"] = {
      diagnostics = {
        disabled = { "inactive-code" }, -- Disables the inactive code highlighting
      },
    },
  },
})

enable_lsp_config('starpls', {
  root_dir = function(bufnr, on_dir)
    if starlark_root(bufnr, buck2_starlark_markers) then
      return
    end

    local root = starlark_root(bufnr, bazel_starlark_markers)
    if root then
      on_dir(root)
    end
  end,
})

enable_lsp_config('buck2', {
  cmd = function(dispatchers, config)
    return vim.lsp.rpc.start(buck2_lsp_cmd(config.root_dir), buck2_lsp_dispatchers(dispatchers), {
      cwd = config.root_dir,
    })
  end,
  root_dir = function(bufnr, on_dir)
    local root = starlark_root(bufnr, buck2_starlark_markers)
    if root and buck2_lsp_cmd(root) then
      on_dir(root)
    end
  end,
})
enable_lsp_config('bazelrc_lsp')
enable_lsp_config('protols')
enable_lsp_config('ts_ls')

local data_pack_root = vim.fs.joinpath(vim.fn.stdpath('data'), 'site', 'pack', 'core', 'opt')
enable_lsp_config('lua_ls', {
  settings = {
    Lua = {
      diagnostics = {
        globals = { "vim" },
        unusedLocalExclude = { "_*" },
      },
      runtime = {
        version = "LuaJIT",
        path = vim.list_extend(
          vim.split(package.path, ';'),
          { "lua/?.lua", "lua/?/init.lua" }
        ),
      },
      telemetry = {
        enable = false
      },
      workspace = {
        checkThirdParty = false,
        library = {
          vim.env.VIMRUNTIME,
          vim.fs.joinpath(data_pack_root, "neotest", "lua"),
          vim.fs.joinpath(data_pack_root, "plenary.nvim", "lua"),
          vim.fs.joinpath(data_pack_root, "nvim-lspconfig", "lua"),
          vim.fs.joinpath(data_pack_root, "nvim-cmp", "lua"),
        }
      },
    }
  }
})

local cmp_ready = false

local function snippet_can_jump(direction)
  if not vim.snippet or type(vim.snippet.active) ~= 'function' then
    return false
  end

  local ok, active = pcall(vim.snippet.active, { direction = direction })
  if ok then
    return active
  end

  ok, active = pcall(vim.snippet.active, direction)
  return ok and active or false
end

local function ensure_cmp()
  if cmp_ready then
    return
  end

  pack_add_once('cmp', { 'nvim_cmp', 'cmp_buffer', 'cmp_path' })

  local cmp = require('cmp')
  local compare = require('cmp.config.compare')

  cmp.setup({
    -- Keep LSP preselect enabled, but sort so the highlighted item is more likely
    -- to be near the top (match LSP sortText before grouping by kind).
    preselect = cmp.PreselectMode.Item,
    sorting = {
      comparators = {
        compare.offset,
        compare.exact,
        compare.score,
        compare.recently_used,
        compare.locality,
        compare.sort_text,
        compare.kind,
        compare.length,
        compare.order,
      },
    },
    snippet = {
      expand = function(args)
        if vim.snippet and type(vim.snippet.expand) == 'function' then
          vim.snippet.expand(args.body)
          return
        end
        vim.notify('No snippet engine available (need Neovim 0.10+ vim.snippet)', vim.log.levels.WARN)
      end,
    },
    -- Put LSP items ahead of plain buffer-word ("Text") items by separating
    -- sources into groups; group 1 is shown before group 2.
    sources = cmp.config.sources(
      {
        { name = 'nvim_lsp' },
        { name = 'path' },
      },
      {
        { name = 'buffer', keyword_length = 2 },
      }
    ),
    mapping = cmp.mapping.preset.insert({
      -- confirm completion item
      ['<Enter>'] = cmp.mapping.confirm({ select = true }),
      -- trigger completion menu
      ['<C-Space>'] = cmp.mapping.complete(),

      -- Jump between LSP snippet placeholders (e.g. gopls function params).
      ['<Tab>'] = cmp.mapping(function(fallback)
        if snippet_can_jump(1) then
          vim.snippet.jump(1)
        else
          fallback()
        end
      end, { "i", "s" }),
      ['<S-Tab>'] = cmp.mapping(function(fallback)
        if snippet_can_jump(-1) then
          vim.snippet.jump(-1)
        else
          fallback()
        end
      end, { "i", "s" }),

      -- scroll up and down the documentation window
      ['<C-u>'] = cmp.mapping.scroll_docs(-4),
      ['<C-d>'] = cmp.mapping.scroll_docs(4),

      -- Custom mapping for Ctrl-J to select next item
      ['<C-j>'] = cmp.mapping(function(fallback)
        if cmp.visible() then
          cmp.select_next_item()
        else
          fallback()
        end
      end, { "i", "s" }),

      -- Optionally map Ctrl-K to select previous item
      ['<C-k>'] = cmp.mapping(function(fallback)
        if cmp.visible() then
          cmp.select_prev_item()
        else
          fallback()
        end
      end, { "i", "s" }),
    }),
  })

  cmp_ready = true
end

vim.api.nvim_create_autocmd('InsertEnter', {
  group = vim.api.nvim_create_augroup('LazyCmp', { clear = true }),
  callback = ensure_cmp,
  once = true,
})

-- Use the default handler but prefer the location list instead of the quickfix
-- window.  The built-in helper `vim.lsp.util.locations_to_items` does not care
-- whether the list is a location- or quickfix-list, the choice is made by the
-- caller via `setloclist` / `setqflist`.

do
  local default_handler = vim.lsp.handlers["textDocument/references"]

  ---@diagnostic disable-next-line: duplicate-set-field
  vim.lsp.handlers["textDocument/references"] = function(err, result, ctx, config)
    config = config or {}
    config.loclist = true
    return default_handler(err, result, ctx, config)
  end
end

-- For copilot
-- https://old.reddit.com/r/neovim/comments/wbx4r6/has_anyone_managed_to_use_github_copilot_in_nvchad/
vim.g.copilot_assume_mapped = true

-- >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> fzf.vim >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
--  Doc: https://github.com/junegunn/fzf.vim
--  Make fzf use neovim floating window
local fzf_lua_ready = false
local fzf_lua_commands = { 'FzfLua', 'Commands', 'Buffers', 'Tags' }

local function delete_fzf_lua_commands()
  for _, command in ipairs(fzf_lua_commands) do
    pcall(vim.api.nvim_del_user_command, command)
  end
end

local function ensure_fzf_lua()
  if not loaded_pack_groups.fzf_lua then
    delete_fzf_lua_commands()
  end
  pack_add_once('fzf_lua', { 'nvim_web_devicons', 'fzf_lua' })

  if not fzf_lua_ready then
    pcall(require, "nvim-web-devicons")
    require("fzf-lua").setup({ "fzf-vim" })
    fzf_lua_ready = true
  end

  return require("fzf-lua")
end

vim.api.nvim_create_user_command('FzfLua', function(command_opts)
  ensure_fzf_lua()
  require("fzf-lua.cmd").run_command(unpack(command_opts.fargs))
end, {
  nargs = '*',
  range = true,
})

for _, command in ipairs({ 'Commands', 'Buffers', 'Tags' }) do
  vim.api.nvim_create_user_command(command, function(command_opts)
    ensure_fzf_lua()
    vim.api.nvim_cmd({
      cmd = command,
      args = command_opts.fargs,
      bang = command_opts.bang,
    }, {})
  end, {
    nargs = '*',
    bang = true,
  })
end

local opts = { noremap = true, silent = false }
local silent_opts = { noremap = true, silent = true }

-- Some QoL shortcuts
map('n', '<leader>a', function() ensure_fzf_lua().commands() end, opts)
map('n', '<leader>b', function() ensure_fzf_lua().buffers() end, opts)
map('n', '<leader>f', function() ensure_fzf_lua().files() end, opts)
map('n', '<leader>r', function() ensure_fzf_lua().grep_cword() end, silent_opts)
map('n', '<leader>t', function()
  ensure_fzf_lua().tags({ query = vim.fn.expand('<cword>') })
end, silent_opts)

-- Key mappings for Airline Tab navigation
vim.api.nvim_set_keymap('n', '<leader>1', '<Plug>AirlineSelectTab1<CR>', opts)
vim.api.nvim_set_keymap('n', '<leader>2', '<Plug>AirlineSelectTab2<CR>', opts)
vim.api.nvim_set_keymap('n', '<leader>3', '<Plug>AirlineSelectTab3<CR>', opts)
vim.api.nvim_set_keymap('n', '<leader>4', '<Plug>AirlineSelectTab4<CR>', opts)
vim.api.nvim_set_keymap('n', '<leader>5', '<Plug>AirlineSelectTab5<CR>', opts)
vim.api.nvim_set_keymap('n', '<leader>6', '<Plug>AirlineSelectTab6<CR>', opts)
vim.api.nvim_set_keymap('n', '<leader>7', '<Plug>AirlineSelectTab7<CR>', opts)
vim.api.nvim_set_keymap('n', '<leader>8', '<Plug>AirlineSelectTab8<CR>', opts)
vim.api.nvim_set_keymap('n', '<leader>9', '<Plug>AirlineSelectTab9<CR>', opts)
vim.api.nvim_set_keymap('n', '<leader>-', '<Plug>AirlineSelectPrevTab<CR>', opts)
vim.api.nvim_set_keymap('n', '<leader>+', '<Plug>AirlineSelectNextTab<CR>', opts)

-- >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> TreeSitter >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
local treesitter_ready = false
local function ensure_treesitter()
  if treesitter_ready then
    return
  end

  pack_add_once('treesitter', { 'nvim_treesitter', 'playground' })

  local parser_config = require "nvim-treesitter.parsers".get_parser_configs()
  parser_config.bazelrc = {
    install_info = {
      url = vim.fs.normalize(vim.fn.expand("~/work/misc/tree-sitter-bazelrc")),
      files = { "src/parser.c" },
      branch = "main",                        -- default branch in case of git repo if different from master
      generate_requires_npm = false,          -- if stand-alone parser without npm dependencies
      requires_generate_from_grammar = false, -- if folder contains pre-generated src/parser.c
    },
    filetype = "bazelrc",
  }
  require 'nvim-treesitter.configs'.setup {
    ensure_installed = {
      'bash',
      'bazelrc',
      'c',
      'cpp',
      'css',
      'diff',
      'dockerfile',
      'git_config',
      'git_rebase',
      'gitattributes',
      'gitcommit',
      'gitignore',
      'go',
      'gomod',
      'gosum',
      'gotmpl',
      'helm',
      'html',
      'hyprlang',
      'java',
      'javascript',
      'jq',
      'json',
      'jsonc',
      'lua',
      'make',
      'markdown',
      'markdown_inline',
      'proto',
      'python',
      'query',
      'regex',
      'rust',
      'scala',
      'sql',
      'starlark',
      'terraform',
      'toml',
      'tsx',
      'typescript',
      'vim',
      'vimdoc',
      'xml',
      'yaml',
    },
    -- Install parsers synchronously (only applied to `ensure_installed`)
    sync_install = false,
    highlight = {
      enable = true, -- false will disable the whole extension
    },
    ignore_install = { "ipkg" },
    incremental_selection = {
      enable = true,
      keymaps = {
        init_selection = "<A-J>", -- set to `false` to disable one of the mappings
        scope_incremental = false,
        node_incremental = "<A-J>",
        node_decremental = "<A-K>",
      },
    },
    playground = {
      enable = true,
      disable = {},
      updatetime = 25,         -- Debounced time for highlighting nodes in the playground from source code
      persist_queries = false, -- Whether the query persists across vim sessions
      keybindings = {
        toggle_query_editor = 'o',
        toggle_hl_groups = 'i',
        toggle_injected_languages = 't',
        toggle_anonymous_nodes = 'a',
        toggle_language_display = 'I',
        focus_language = 'f',
        unfocus_language = 'F',
        update = 'R',
        goto_node = '<cr>',
        show_help = '?',
      },
    },
    query_linter = {
      enable = true,
      use_virtual_text = true,
      lint_events = { "BufWrite", "CursorHold" },
    }
  }

  treesitter_ready = true
end

local treesitter_group = vim.api.nvim_create_augroup('LazyTreesitter', { clear = true })
vim.api.nvim_create_autocmd('FileType', {
  group = treesitter_group,
  callback = ensure_treesitter,
})
vim.api.nvim_create_autocmd('CmdUndefined', {
  group = treesitter_group,
  pattern = 'TS*',
  callback = ensure_treesitter,
})


-- >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Language Settings >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

-- Bazel (bzl) settings
vim.api.nvim_create_autocmd('FileType', {
  pattern = 'bzl',
  callback = function()
    vim.opt_local.expandtab = true
    vim.opt_local.shiftwidth = 4
    vim.opt_local.softtabstop = 4
    vim.opt_local.tabstop = 4
  end
})
-- Bazelrc (bazelrc) settings
vim.api.nvim_create_augroup('BazelRcFiletype', { clear = true })
vim.api.nvim_create_autocmd({ 'BufRead', 'BufNewFile' }, {
  group = 'BazelRcFiletype',
  pattern = '*.bazelrc',
  callback = function()
    vim.bo.filetype = 'bazelrc'
  end,
})

-- Enable filetype plugins
vim.cmd('filetype plugin on')

local function source_vim_go_runtime(filetype)
  for _, runtime in ipairs({
    { directory = 'ftplugin', guard = 'did_ftplugin' },
    { directory = 'indent', guard = 'did_indent' },
  }) do
    local runtime_file = runtime.directory .. '/' .. filetype .. '.vim'
    for _, path in ipairs(vim.api.nvim_get_runtime_file(runtime_file, true)) do
      if path:find('/vim-go/', 1, true) then
        local previous_guard = vim.b[runtime.guard]
        vim.b[runtime.guard] = nil
        vim.cmd.source(vim.fn.fnameescape(path))
        if vim.b[runtime.guard] == nil then
          vim.b[runtime.guard] = previous_guard
        end
      end
    end
  end

  if filetype == 'go' then
    for _, path in ipairs(vim.api.nvim_get_runtime_file('ftplugin/go/*.vim', true)) do
      if path:find('/vim-go/', 1, true) then
        vim.cmd.source(vim.fn.fnameescape(path))
      end
    end
  end
end

vim.api.nvim_create_autocmd('FileType', {
  pattern = {
    'go',
    'gomod',
    'gosum',
    'gowork',
    'gotmpl',
    'gohtmltmpl',
    'godoc',
    'asm',
  },
  callback = function(args)
    local source_late_runtime = not loaded_pack_groups.vim_go
    pack_add_once('vim_go', { 'vim_go' })

    if source_late_runtime then
      source_vim_go_runtime(args.match)
    end
  end,
})

-- Golang settings
vim.api.nvim_create_autocmd('FileType', {
  pattern = 'go',
  callback = function(args)
    vim.opt_local.expandtab = false
    vim.opt_local.shiftwidth = 2
    vim.opt_local.softtabstop = 2
    vim.opt_local.tabstop = 2
    vim.b[args.buf].editorconfig = false
  end
})

-- Markdown settings
vim.api.nvim_create_autocmd('FileType', {
  pattern = 'markdown',
  callback = function()
    vim.opt_local.wrap = true
  end
})

-- Java settings
vim.api.nvim_create_autocmd('FileType', {
  pattern = 'java',
  callback = function()
    vim.opt_local.expandtab = true
    vim.opt_local.shiftwidth = 2
    vim.opt_local.softtabstop = 2
    vim.opt_local.tabstop = 2
  end
})

vim.cmd [[
  " sourcegraph
  function! GetCodeSearchURL(config) abort
      " BazelBuild specific
      if a:config['remote'] =~ '^\%(https\=://\|git://\|git@\)github\.com[/:]bazelbuild/bazel\zs.\{-\}\ze\%(\.git\)\=$'
          let commit = a:config['commit']
          let path = a:config['path']
          let url = printf("https://cs.opensource.google/bazel/bazel/+/%s:%s",
              \ commit,
              \ path)
          let fromLine = a:config['line1']
          let toLine = a:config['line2']
          if fromLine > 0 && fromLine == toLine
              let url .= ';l=' . fromLine
          elseif toLine > 0
              let url .= ';l=' . fromLine . '-' . toLine
          endif
          return url
      endif

      " Use GitHub default browsing
      if a:config['remote'] =~ '^\(https://\|git@\)github.com'
          let repository = substitute(matchstr(a:config['remote'], 'github\.com.*'), ':', '/', '')
          let repository = substitute(repository, '.git', '', '')
          let commit = a:config['commit']
          let path = a:config['path']
          let githubUrl = printf("https://%s/blob/%s/%s",
              \ repository,
              \ commit,
              \ path)
          let fromLine = a:config['line1']
          let toLine = a:config['line2']
          if fromLine > 0 && fromLine == toLine
              let githubUrl .= '#L' . fromLine
          elseif toLine > 0
              let githubUrl .= '#L' . fromLine . '-' . 'L' . toLine
          endif
          return githubUrl
      endif

      " Mostly use for Gitlab stuffs
      if a:config['remote'] =~ '^\(https://\|git@\)\(github\|gitlab\).com'
          let repository = substitute(matchstr(a:config['remote'], '\(github\|gitlab\)\.com.*'), ':', '/', '')
          let repository = substitute(repository, '.git', '', '')
          let commit = a:config['commit']
          let path = a:config['path']
          let sourcegraphUrl = printf("https://sourcegraph.com/%s@%s/-/blob/%s",
              \ repository,
              \ commit,
              \ path)
          let fromLine = a:config['line1']
          let toLine = a:config['line2']
          if fromLine > 0 && fromLine == toLine
              let sourcegraphUrl .= '#L' . fromLine
          elseif toLine > 0
              let sourcegraphUrl .= '#L' . fromLine . '-' . toLine
          endif
          return sourcegraphUrl
      endif

      return ''
  endfunction
  if !exists('g:fugitive_browse_handlers')
      let g:fugitive_browse_handlers = []
  endif
  if index(g:fugitive_browse_handlers, function('GetCodeSearchURL')) < 0
      call insert(g:fugitive_browse_handlers, function('GetCodeSearchURL'))
  endif
]]

-- >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Neotest-Bazel >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
local neotest_ready = false
local function ensure_neotest()
  pack_add_once('neotest', { 'plenary', 'nvim_nio', 'neotest', 'neotest_bazel' })

  local neotest = require("neotest")
  if not neotest_ready then
    neotest.setup({
      adapters = {
        require("neotest-bazel")
      },
      discovery = {
        concurrent = 1,
        enabled = false,
      },
      running = {
        concurrent = false,
      },
      log_level = vim.log.levels.DEBUG,
    })
    neotest_ready = true
  end

  return neotest
end

vim.keymap.set('n', '<leader>tr', function() ensure_neotest().run.run() end, {})
vim.keymap.set('n', '<leader>tf', function() ensure_neotest().run.run(vim.fn.expand("%")) end, {})
vim.keymap.set('n', '<leader>ts', function() ensure_neotest().summary.toggle() end, {})
vim.keymap.set('n', '<leader>to', function() ensure_neotest().output_panel.toggle() end, {})
