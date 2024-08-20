local vim = vim

-- Disable unused providers
vim.g.loaded_ruby_provider = 0
vim.g.loaded_perl_provider = 0
vim.g.loaded_node_provider = 0

-- >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Plugins >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
--  Doc: https://github.com/junegunn/vim-plug

local Plug = vim.fn['plug#']

vim.call('plug#begin')

-- Utilities
Plug('lewis6991/fileline.nvim')

Plug('ibhagwan/fzf-lua', { ['branch'] = 'main' })
Plug('nvim-tree/nvim-web-devicons')
Plug('junegunn/vim-peekaboo')

Plug('tpope/vim-fugitive')
Plug('tpope/vim-surround')
Plug('tpope/vim-repeat')

-- Indentation
Plug('lukas-reineke/indent-blankline.nvim', { ['main'] = 'ibl', ['opts'] = {} })

-- Status bar
Plug('vim-airline/vim-airline')
Plug('airblade/vim-gitgutter', { ['branch'] = 'main' })

-- TreeSitter
Plug('nvim-treesitter/nvim-treesitter', { ['do'] = ':TSUpdate' })
Plug('nvim-treesitter/playground')

-- LSP Client
Plug('VonHeikemen/lsp-zero.nvim')
Plug('delphinus/cmp-ctags')
Plug('hrsh7th/cmp-buffer')
Plug('hrsh7th/cmp-nvim-lsp')
Plug('hrsh7th/nvim-cmp')
Plug('neovim/nvim-lspconfig')

-- Sneak
Plug('justinmk/vim-sneak')

-- Copilot
Plug('github/copilot.vim')

-- Golang
Plug('fatih/vim-go')

-- Neotest
Plug 'nvim-lua/plenary.nvim'
Plug 'antoinemadec/FixCursorHold.nvim'
Plug 'nvim-neotest/nvim-nio'
Plug 'nvim-neotest/neotest'

-- Bazel / Ctags
Plug('ludovicchabant/vim-gutentags')
Plug('dhananjaylatkar/cscope_maps.nvim')

-- Coloring
Plug('joshdick/onedark.vim', { ['branch'] = 'main' })

vim.call('plug#end')

-- >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Editor Settings >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

-- Set options
vim.opt.compatible = false
vim.opt.ruler = true
vim.opt.hidden = true
vim.opt.cmdheight = 2
vim.opt.history = 9000
vim.opt.signcolumn = "auto"
vim.opt.number = true
vim.opt.relativenumber = true
vim.opt.clipboard:append("unnamedplus")
vim.opt.scrolloff = 5

-- Set clipboard control for Unix
if vim.fn.has('macunix') == 0 and vim.fn.has('unix') == 1 then
  vim.g.clipboard = {
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
vim.opt.backup = false
vim.opt.writebackup = false
vim.opt.swapfile = false

-- Indentation
vim.opt.autoindent = true
vim.opt.smartindent = true

-- Search default
vim.opt.ignorecase = true
vim.opt.smartcase = true

-- Shortcuts
-- vim.g.mapleader = ";"

-- Fast way to escape
vim.api.nvim_set_keymap('i', 'jj', '<Esc>', { noremap = true, silent = true })

-- Split window behavior
vim.opt.splitbelow = true
vim.opt.splitright = true

-- Don't use Ex mode
vim.api.nvim_set_keymap('n', 'Q', '<Nop>', { noremap = true, silent = true })

-- Color and autocmd for color scheme
if vim.fn.has("autocmd") == 1 then
  vim.cmd([[
    augroup colorextend
      autocmd!
      let s:off_white = { "gui": "#ABB2BF", "cterm": "145", "cterm16" : "7" }
      autocmd ColorScheme * call onedark#set_highlight("LspInlayHint", { "fg": s:off_white })
    augroup END
  ]])
end

vim.env.NVIM_TUI_ENABLE_TRUE_COLOR = 1
vim.cmd("colorscheme onedark")

-- >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> LSP Config >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
-- remove the default keymaps from https://github.com/neovim/neovim/pull/28650
vim.keymap.del("n", "grn")
vim.keymap.del("n", "grr")
vim.keymap.del({ "v", "n" }, "gra")

vim.lsp.inlay_hint.enable(not vim.lsp.inlay_hint.is_enabled())

local lsp_zero = require('lsp-zero')
lsp_zero.on_attach(function(_client, bufnr)
  lsp_zero.default_keymaps({ buffer = bufnr })
end)
lsp_zero.extend_lspconfig({
  sign_text = true,
})

local lspconfig = require 'lspconfig'
lspconfig.gopls.setup {
  settings = {
    gopls = {
      usePlaceholders = true,
      buildFlags = { "-tags=linux" },
      -- ["local"] = "github.com/buildbuddy-io/buildbuddy",
      staticcheck = true,
      analyses = {
        unusedparams = true,
      },
      directoryFilters = {
        "-bazel-bin",
        "-bazel-out",
        "-bazel-buildbuddy",
        "-bazel-testlog",
      },
      vulncheck = "Imports",
      completeUnimported = true,
      experimentalPostfixCompletions = true,
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
}
lspconfig.rust_analyzer.setup {}
lspconfig.starpls.setup {}
lspconfig["bazelrc-lsp"].setup {}
lspconfig.pbls.setup {}
lspconfig.tsserver.setup {}
local lua_opts = lsp_zero.nvim_lua_ls()
lspconfig.lua_ls.setup(lua_opts)

local cmp = require('cmp')
cmp.setup({
  -- if you don't know what is a "source" in nvim-cmp read this:
  -- https://github.com/VonHeikemen/lsp-zero.nvim/blob/v3.x/doc/md/autocomplete.md#adding-a-source
  sources = {
    { name = 'path' },
    { name = 'nvim_lsp' },
    { name = 'buffer',  keyword_length = 2 },
    { name = 'ctags' },
  },
  mapping = cmp.mapping.preset.insert({
    -- confirm completion item
    ['<Enter>'] = cmp.mapping.confirm({ select = true }),
    -- trigger completion menu
    ['<C-Space>'] = cmp.mapping.complete(),

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
  -- note: if you are going to use lsp-kind (another plugin)
  -- replace the line below with the function from lsp-kind
  formatting = lsp_zero.cmp_format(),
})

local on_references = vim.lsp.handlers["textDocument/references"]
vim.lsp.handlers["textDocument/references"] = vim.lsp.with(
  on_references, {
    -- Use location list instead of quickfix list
    loclist = true,
  }
)

-- >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Ctags >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
--  Use Gutentags(ctags) for projects that are not friendly to LSP
require("cscope_maps").setup()

-- Set gutentags cache directory
vim.g.gutentags_cache_dir = vim.fn.expand('~/.cache/vim/ctags/')

-- Set gutentags modules
vim.g.gutentags_modules = { 'ctags', 'cscope_maps' }

-- Set gutentags file list command
vim.g.gutentags_file_list_command = 'fd "(bazelrc|WORKSPACE|BUILD|\\.(java|cc|c|h|am|sh|bash|star|bazel|bzl|proto|py)$)"'

-- Enable cscope inverted index maps
vim.g.gutentags_cscope_build_inverted_index_maps = 1

-- Set gutentags ctag tagfile
vim.g.gutentags_ctag_tagfile = '.git/ctags'

-- Exclude specific paths from ctags
vim.g.gutentags_ctags_exclude = { '*/bazel-out/*', '*/bazel-bin/*' }

-- Enable gutentags for specific directories
vim.g.gutentags_enabled_dirs = { '/Users/sluongng/work/bazelbuild/bazel' }

vim.cmd [[
  let g:gutentags_init_user_func = 'CheckEnabledDirs'
  function! CheckEnabledDirs(file) abort
      let file_path = fnamemodify(a:file, ':p:h')
      for enabled_dir in g:gutentags_enabled_dirs
          let enabled_path = fnamemodify(enabled_dir, ':p:h')
          if match(file_path, enabled_path) == 0
              return 1
          endif
      endfor
      return 0
  endfunction
]]


-- >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> fzf.vim >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
--  Doc: https://github.com/junegunn/fzf.vim
--  Make fzf use neovim floating window
require("fzf-lua").setup({ "fzf-vim" })

local opts = { noremap = true, silent = false }
local silent_opts = { noremap = true, silent = true }

-- Some QoL shortcuts
vim.api.nvim_set_keymap('n', '<leader>a', ':Commands<CR>', opts)
vim.api.nvim_set_keymap('n', '<leader>b', ':Buffers<CR>', opts)
vim.api.nvim_set_keymap('n', '<leader>f', ':FzfLua files<CR>', opts)
vim.api.nvim_set_keymap('n', '<leader>r', ':FzfLua grep search=<C-R><C-W><CR>', silent_opts)
vim.api.nvim_set_keymap('n', '<leader>t', ':Tags <C-R><C-W><CR>', silent_opts)


-- >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Airline >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
-- Doc: https://github.com/vim-airline/vim-airline

-- Enable Tab on top
vim.g['airline#extensions#tabline#enabled'] = 1
vim.g['airline#extensions#tabline#buffer_idx_mode'] = 1

-- Key mappings for Airline Tab navigation

vim.api.nvim_set_keymap('n', '<leader>1', '<Plug>AirlineSelectTab1', opts)
vim.api.nvim_set_keymap('n', '<leader>2', '<Plug>AirlineSelectTab2', opts)
vim.api.nvim_set_keymap('n', '<leader>3', '<Plug>AirlineSelectTab3', opts)
vim.api.nvim_set_keymap('n', '<leader>4', '<Plug>AirlineSelectTab4', opts)
vim.api.nvim_set_keymap('n', '<leader>5', '<Plug>AirlineSelectTab5', opts)
vim.api.nvim_set_keymap('n', '<leader>6', '<Plug>AirlineSelectTab6', opts)
vim.api.nvim_set_keymap('n', '<leader>7', '<Plug>AirlineSelectTab7', opts)
vim.api.nvim_set_keymap('n', '<leader>8', '<Plug>AirlineSelectTab8', opts)
vim.api.nvim_set_keymap('n', '<leader>9', '<Plug>AirlineSelectTab9', opts)
vim.api.nvim_set_keymap('n', '<leader>-', '<Plug>AirlineSelectPrevTab', opts)
vim.api.nvim_set_keymap('n', '<leader>+', '<Plug>AirlineSelectNextTab', opts)

-- Extension: LSP and Gutentags
vim.g['airline#extensions#nvimlsp#enabled'] = 1
vim.g['airline#extensions#gutentags#enabled'] = 1


-- >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> TreeSitter >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
require 'nvim-treesitter.configs'.setup {
  ensure_installed = "all",
  -- Install parsers synchronously (only applied to `ensure_installed`)
  sync_install = false,
  highlight = {
    enable = true, -- false will disable the whole extension
  },
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

-- Enable filetype plugins
vim.cmd('filetype plugin on')

-- Golang settings
vim.api.nvim_create_autocmd('FileType', {
  pattern = 'go',
  callback = function()
    vim.opt_local.expandtab = false
    vim.opt_local.shiftwidth = 2
    vim.opt_local.softtabstop = 2
    vim.opt_local.tabstop = 2
    vim.g.editorconfig = false
  end
})

-- Golang syntax highlighting
vim.g.go_highlight_functions = 1
vim.g.go_highlight_function_parameters = 1
vim.g.go_highlight_function_calls = 1
vim.g.go_highlight_types = 1
vim.g.go_highlight_extra_types = 1
vim.g.go_highlight_fields = 1
vim.g.go_highlight_methods = 1
vim.g.go_highlight_operators = 1
vim.g.go_highlight_structs = 1
vim.g.go_highlight_generate_tags = 1
vim.g.go_highlight_format_strings = 1
vim.g.go_highlight_variable_declarations = 1
vim.g.go_highlight_variable_assignments = 1
vim.g.go_highlight_build_constraints = 1
vim.g.go_highlight_array_whitespace_error = 1
vim.g.go_highlight_chan_whitespace_error = 1

-- Golang additional settings
vim.g.go_auto_sameids = 0
vim.g.go_def_mapping_enabled = 0
vim.g.go_fmt_command = "gopls"
vim.g.go_gopls_enabled = 0
vim.g.go_gopls_gofumpt = 0

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
-- A simple Bazel adapter for Neotest
local logger = require("neotest.logging")

local BazelAdapter = {}

---Find the project root directory given a current directory to work from.
---Should no root be found, the adapter can still be used in a non-project context if a test file matches.
---@async
---@param _dir string @Directory to treat as cwd
---@return string | nil @Absolute root dir of test suite
function BazelAdapter.root(_dir)
  local root = vim.system({ 'bazel', 'info', 'workspace' }, { text = true }):wait().stdout
  if root == nil then
    return nil
  end
  root = vim.trim(root)
  if root == '' then
    return nil
  end
  return root
end

---Filter directories when searching for test files
---Use bazel query --output=package to find if the directory is a package
---@async
---@param _name string Name of directory
---@param rel_path string Path to directory, relative to root
---@param _root string Root directory of project
---@return boolean
function BazelAdapter.filter_dir(_name, rel_path, _root)
  local result = vim.system({
    'bazel', 'query',
    '--bes_results_url=', '--bes_backend=',
    '--output=package',
    rel_path
  }, { text = true }):wait()
  return result.code == 0
end

---@class Bazel.file_info
---@field package string
---@field file_target string
---@field test_target string | nil
---@field target_name string | nil

---@async
---@param file_path string
---@return Bazel.file_info
local get_file_info = function(file_path)
  local path = require("plenary.path")
  ---@type string
  local relative_path = path.new(file_path):make_relative(vim.fn.getcwd())

  local file_info = {}

  local result = vim.system({
    'bazel', 'query',
    '--bes_results_url=', '--bes_backend=',
    '--output=package',
    relative_path
  }, { text = true }):wait()
  local bazel_package = vim.trim(result.stdout)
  if bazel_package == '' then
    return file_info
  end
  file_info.package = bazel_package

  result = vim.system({
    'bazel', 'query',
    '--bes_results_url=', '--bes_backend=',
    '--output=label',
    relative_path
  }, { text = true }):wait()
  local label = vim.trim(result.stdout)
  if label == '' then
    return file_info
  end
  file_info.label = label

  local test_query = 'tests(rdeps(' .. bazel_package .. ':all, ' .. label .. ', 1))'
  result = vim.system({
    'bazel', 'query',
    '--bes_results_url=', '--bes_backend=',
    '--infer_universe_scope', '--order_output=no',
    test_query
  }, { text = true }):wait()
  local test_target = vim.trim(result.stdout)
  file_info.test_target = test_target

  -- Turn '//foo/bar:baz' into 'baz'
  file_info.target_name = test_target:match(":(.*)$")

  return file_info
end

---Check if a file is a test file using 2 bazel query
---1. Find the target label of the file using --output=label
---2. Check if the target is a test target using 'tests()' and 'deps()' in Bazel query
---
---For example,
---  ```shell
---  bazel query --output=package server/util/subdomain/subdomain_test.go
---  bazel query --output=label server/util/subdomain/subdomain_test.go
---
---  bazel query --infer_universe_scope --order_output=no \
---    'tests(rdeps(server/util/subdomain:all, //server/util/subdomain:subdomain_test.go, 1)'
---  ```
---@async
---@param file_path string
---@return boolean
function BazelAdapter.is_test_file(file_path)
  local file_info = get_file_info(file_path)
  return file_info.test_target ~= nil and file_info.test_target ~= ''
end

--- This was taken from neotest
local function get_match_type(captured_nodes)
  if captured_nodes["test.name"] then
    return "test"
  end
  if captured_nodes["namespace.name"] then
    return "namespace"
  end
end

--- Build the tree position from the captured nodes manually
--- so that we could scrub the quotes from the name.
---
--- This was taken from neotest with some modifications
local function build_position(file_path, source, captured_nodes)
  local match_type = get_match_type(captured_nodes)
  if match_type then
    ---@type string
    local name = vim.treesitter.get_node_text(captured_nodes[match_type .. ".name"], source)
    name = name:gsub('"', "") -- Remove quotes
    local definition = captured_nodes[match_type .. ".definition"]

    return {
      type = match_type,
      path = file_path,
      name = name,
      range = { definition:range() },
    }
  end
end

---Given a file path, parse all the tests within it by using different tree-sitter persist_queries
---for different languages based on file extension.
---Currently support: Go, Java
---@async
---@param file_path string Absolute file path
---@return neotest.Tree | nil
function BazelAdapter.discover_positions(file_path)
  local lib = require("neotest.lib")
  local ext = vim.filetype.match({ filename = file_path })
  if ext == "go" then
    local test_func_query = [[
;; query
((function_declaration
  name: (identifier) @test.name) (#match? @test.name "^(Test|Example)"))
  @test.definition
]]
    local subtest_query = [[
;; query
(call_expression
  function: (selector_expression
    field: (field_identifier) @test.method) (#match? @test.method "^Run$")
  arguments: (argument_list . (interpreted_string_literal) @test.name))
  @test.definition
]]
    local test_table_query = [[
;; query
(block
  (short_var_declaration
    left: (expression_list
      (identifier) @test.cases)
    right: (expression_list
      (composite_literal
        (literal_value
          (literal_element
            (literal_value
              (keyed_element
                (literal_element
                  (identifier) @test.field.name)
                (literal_element
                  (interpreted_string_literal) @test.name)))) @test.definition))))
  (for_statement
    (range_clause
      left: (expression_list
        (identifier) @test.case)
      right: (identifier) @test.cases1
        (#eq? @test.cases @test.cases1))
    body: (block
     (expression_statement
      (call_expression
        function: (selector_expression
          field: (field_identifier) @test.method)
          (#match? @test.method "^Run$")
        arguments: (argument_list
          (selector_expression
            operand: (identifier) @test.case1
            (#eq? @test.case @test.case1)
            field: (field_identifier) @test.field.name1
            (#eq? @test.field.name @test.field.name1))))))))
]]
    local list_test_table_wrapped_query = [[
;; query
(for_statement
  (range_clause
      left: (expression_list
        (identifier)
        (identifier) @test.case )
      right: (composite_literal
        type: (slice_type
          element: (struct_type
            (field_declaration_list
              (field_declaration
                name: (field_identifier)
                type: (type_identifier)))))
        body: (literal_value
          (literal_element
            (literal_value
              (keyed_element
                (literal_element
                  (identifier))  @test.field.name
                (literal_element
                  (interpreted_string_literal) @test.name ))
              ) @test.definition)
          )))
    body: (block
      (expression_statement
        (call_expression
          function: (selector_expression
            operand: (identifier)
            field: (field_identifier))
          arguments: (argument_list
            (selector_expression
              operand: (identifier)
              field: (field_identifier) @test.field.name1) (#eq? @test.field.name @test.field.name1))))))
]]
    local test_table_inline_struct_query = [[
;; query
(for_statement
  (range_clause
    right: (composite_literal
      type: (slice_type
        element: (struct_type
          (field_declaration_list
            (field_declaration
              name: (field_identifier) ;; the key of the struct's test name
              type: (type_identifier) @field.type (#eq? @field.type "string")))))
      body: (literal_value
        (literal_element
          (literal_value
            (literal_element
              (interpreted_string_literal) @test.name) @test.definition)))))
  body: (block
    (expression_statement
      (call_expression
        function: (selector_expression
          operand: (identifier)
          field: (field_identifier) @test.method (#match? @test.method "^Run$"))
        arguments: (argument_list
          (selector_expression
            operand: (identifier)
            field: (field_identifier)))))))
]]
    local map_test_table_query = [[
;; query
(block
    (short_var_declaration
      left: (expression_list
        (identifier) @test.cases)
      right: (expression_list
        (composite_literal
          (literal_value
            (keyed_element
            (literal_element
                (interpreted_string_literal)  @test.name)
              (literal_element
                (literal_value)  @test.definition))))))
  (for_statement
     (range_clause
        left: (expression_list
          ((identifier) @test.key.name)
          ((identifier) @test.case))
        right: (identifier) @test.cases1
          (#eq? @test.cases @test.cases1))
      body: (block
         (expression_statement
          (call_expression
            function: (selector_expression
              field: (field_identifier) @test.method)
              (#match? @test.method "^Run$")
              arguments: (argument_list
              ((identifier) @test.key.name1
              (#eq? @test.key.name @test.key.name1))))))))
]]

    local query = test_func_query ..
        subtest_query ..
        test_table_query ..
        list_test_table_wrapped_query ..
        test_table_inline_struct_query ..
        map_test_table_query
    local tree = lib.treesitter.parse_positions(file_path, query, {
      fast = true,
      nested_tests = true,
      build_position = build_position,
    })
    return tree
  elseif ext == "java" then
    local test_class_query = [[
;; query
(class_declaration
  name: (identifier) @namespace.name
) @namespace.definition
]]

    local parameterized_test_query = [[
;; query
(method_declaration
  (modifiers
    (marker_annotation
      name: (identifier) @annotation
        (#any-of? @annotation "Test" "ParameterizedTest" "CartesianTest")
      )
  )
  name: (identifier) @test.name
) @test.definition
]]

    local query = test_class_query .. parameterized_test_query
    return lib.treesitter.parse_positions(file_path, query)
  end
end

-- Converts the AST-detected Neotest node test name into the 'go test' command
-- test name format.
---@param pos_id string
---@return string
local id_to_gotest_name = function(pos_id)
  -- construct the test name
  local test_name = pos_id
  -- Remove the path before ::
  test_name = test_name:match("::(.*)$")
  -- Replace :: with /
  test_name = test_name:gsub("::", "/")
  -- Remove double quotes (single quotes are supported)
  test_name = test_name:gsub('"', "")
  -- Replace any spaces with _
  test_name = test_name:gsub(" ", "_")

  return test_name
end

---@class RunspecContext
---@field language string
---@field file_info Bazel.file_info
---@field test_filter string | nil

---@param args neotest.RunArgs
---@return nil | neotest.RunSpec | neotest.RunSpec[]
function BazelAdapter.build_spec(args)
  local tree = args.tree
  local pos = tree:data()
  local ext = vim.filetype.match({ filename = pos.path })

  if pos.type == "test" then
    if ext == "go" then
      local test_name = id_to_gotest_name(pos.id)
      local file_info = get_file_info(tree:data().path)

      --- @type RunspecContext
      local context = {
        language = "go",
        file_info = file_info,
        test_filter = test_name,
      }
      return {
        command = { "bazel", "test", file_info.test_target, "--test_filter=" .. test_name },
        context = context,
      }
    end
  elseif pos.type == "file" then
    if ext == "go" then
      local file_info = get_file_info(tree:data().path)

      --- @type RunspecContext
      local context = {
        language = "go",
        file_info = file_info,
      }
      return {
        command = { "bazel", "test", file_info.test_target, },
        context = context,
      }
    end
  end

  return nil
end

---@async
---@param spec neotest.RunSpec
---@param _result neotest.StrategyResult
---@param tree neotest.Tree
---@return table<string, neotest.Result>
function BazelAdapter.results(spec, _result, tree)
  local xml = require('neotest.lib.xml')
  local file = require('neotest.lib.file')
  local bazel_testlogs = vim.system({ 'bazel', 'info', 'bazel-testlogs' }, { text = true }):wait().stdout
  if bazel_testlogs == nil then
    return {}
  end

  ---@type string
  local test_log_dir = vim.trim(bazel_testlogs) ..
      '/' .. spec.context.file_info.package .. '/' .. spec.context.file_info.target_name

  local junit_xml = test_log_dir .. '/test.xml'
  local junit_data = xml.parse(file.read(junit_xml))

  local pos = tree:data()
  ---@type table<string, neotest.Result>
  local neotest_results = {}

  for _, testsuite in pairs(junit_data.testsuites) do
    for _, testcase in pairs(testsuite.testcase) do
      logger.debug("Testcase: " .. vim.inspect(testcase))
      local test_name = ''
      if testcase._attr then
        test_name = testcase._attr.name
      else
        test_name = testcase.name
      end
      test_name = test_name:gsub("/", "::")
      local file_name = vim.split(pos.id, '::')[1]
      test_name = file_name .. '::' .. test_name

      if testcase.failure then
        neotest_results[test_name] = {
          status = 'failed',
          output = test_log_dir .. '/' .. 'test.log',
          short = testcase.failure._attr.message,
          errors = {
            {
              message = testcase.failure._attr.message,
              line = pos.range[1],
            },
          },
        }
      else
        neotest_results[test_name] = {
          status = 'passed',
          output = test_log_dir .. '/' .. 'test.log',
        }
      end
    end
  end

  return neotest_results
end

require("neotest").setup({
  adapters = {
    BazelAdapter
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
