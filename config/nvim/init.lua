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
Plug('nvim-lua/plenary.nvim')
Plug('antoinemadec/FixCursorHold.nvim')
Plug('nvim-neotest/nvim-nio')
Plug('nvim-neotest/neotest')
Plug('sluongng/neotest-bazel', { ['dir'] = '~/work/misc/neotest-bazel' })

-- Bazel / Ctags
Plug('ludovicchabant/vim-gutentags')
Plug('dhananjaylatkar/cscope_maps.nvim')

-- Coloring
Plug('joshdick/onedark.vim', { ['branch'] = 'main' })
Plug('towolf/vim-helm')

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

local function on_list(options)
    vim.fn.setqflist({}, ' ', options)
    if #options.items > 1 then
        vim.cmd("botright cwindow") -- always take full width
    end
    vim.cmd.cfirst()
end

local lsp_zero = require('lsp-zero')
lsp_zero.on_attach(function(_client, bufnr)
  local opts = { buffer = bufnr, remap = false }
  lsp_zero.default_keymaps({ buffer = bufnr, exclude = { '<F2>', '<F4>', 'gr', 'gd', 'gD' } })

  vim.keymap.set("n", "<Leader>rn", function() vim.lsp.buf.rename() end, opts)
  vim.keymap.set("n", "<Leader>ca", function() vim.lsp.buf.code_action() end, opts)
  vim.keymap.set("n", "<Leader>cf", function() vim.lsp.buf.format() end, opts)
  vim.keymap.set("n", "gr", function() vim.lsp.buf.references(nil, { on_list = on_list }) end)
  vim.keymap.set("n", "gR", function()
      vim.cmd.vsplit()
      vim.lsp.buf.references(nil, { on_list = on_list })
  end)
  vim.keymap.set("n", "gd", function() vim.lsp.buf.definition({ on_list = on_list }) end)
  vim.keymap.set("n", "gD", function()
      vim.cmd.vsplit()
      vim.lsp.buf.definition({ on_list = on_list })
  end)
  vim.keymap.set('n', '<leader>e', vim.diagnostic.open_float, opts)
  vim.keymap.set('n', '<leader>E', vim.diagnostic.setloclist, opts)
  vim.keymap.set('n', ']d', function()
      vim.diagnostic.goto_next({ float = { border = 'rounded' } }) -- Go to next diagnostic, open float
  end, opts)
end)
lsp_zero.extend_lspconfig({
  sign_text = true,
})

local lspconfig = require 'lspconfig'
lspconfig.gopls.setup {
  settings = {
    gopls = {
      usePlaceholders = true,
      buildFlags = {"-tags=linux,amd64"},
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
lspconfig.rust_analyzer.setup {
  settings = {
    ["rust-analyzer"] = {
      diagnostics = {
        disabled = { "inactive-code" },  -- Disables the inactive code highlighting
      },
    },
  },
}
lspconfig.starpls.setup {}
lspconfig.bazelrc_lsp.setup {}
lspconfig.pbls.setup {
  -- cmd = {"env", "RUST_LOG=trace", "pbls"},
}
lspconfig.ts_ls.setup {}
lspconfig.lua_ls.setup({
  settings = {
    Lua = {
      diagnostics = {
        globals = { "vim" },
        unusedLocalExclude = { "_*" },
      },
      runtime = {
        path = {
          "./?.lua",
          "/Users/sluongng/work/misc/neovim/.deps/usr/share/lua/5.1/?.lua",
          "/Users/sluongng/work/misc/neovim/.deps/usr/share/lua/5.1/?/init.lua",
          "/Users/sluongng/work/misc/neovim/.deps/usr/share/luajit-2.1/?.lua",
          "/usr/local/share/lua/5.1/?.lua",
          "/usr/local/share/lua/5.1/?/init.lua",
          "lua/?.lua",
          "lua/?/init.lua",
        },
        version = "LuaJIT"
      },
      telemetry = {
        enable = false
      },
      workspace = {
        checkThirdParty = false,
        library = {
          "/usr/local/share/nvim/runtime",
          "${3rd}/luv/library",
          "/Users/sluongng/.local/share/nvim/plugged/neotest/lua",
          "/Users/sluongng/.local/share/nvim/plugged/plenary.nvim/lua",
          "/Users/sluongng/.local/share/nvim/plugged/lsp-zero.nvim/lua",
          "/Users/sluongng/.local/share/nvim/plugged/nvim-lspconfig/lua",
          "/Users/sluongng/.local/share/nvim/plugged/nvim-cmp/lua",
        }
      },
    }
  }
})

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
  let g:gutentags_init_user_func = 'CheckEnabledDirs'
]]

-- For copilot 
-- https://old.reddit.com/r/neovim/comments/wbx4r6/has_anyone_managed_to_use_github_copilot_in_nvchad/
vim.g.copilot_assume_mapped = true

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
local parser_config = require "nvim-treesitter.parsers".get_parser_configs()
parser_config.bazelrc = {
  install_info = {
    url = "~/work/misc/tree-sitter-bazelrc",
    files = { "src/parser.c" },
    branch = "main",                        -- default branch in case of git repo if different from master
    generate_requires_npm = false,          -- if stand-alone parser without npm dependencies
    requires_generate_from_grammar = false, -- if folder contains pre-generated src/parser.c
  },
  filetype = "bazelrc",
}
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
local neotest = require("neotest")
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

vim.keymap.set('n', '<leader>tr', function() neotest.run.run() end, {})
vim.keymap.set('n', '<leader>tf', function() neotest.run.run(vim.fn.expand("%")) end, {})
vim.keymap.set('n', '<leader>ts', function() neotest.summary.toggle() end, {})
vim.keymap.set('n', '<leader>to', function() neotest.output_panel.toggle() end, {})
