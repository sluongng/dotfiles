local vim = vim

-- Disable unused providers
vim.g.loaded_ruby_provider = 0
vim.g.loaded_perl_provider = 0
vim.g.loaded_node_provider = 0

-- Golang additional settings
-- Rely on nvim-treesitter for syntax highlighting and nvim-lspconfig for formatting.
vim.g.go_auto_sameids = 0
vim.g.go_def_mapping_enabled = 0
vim.g.go_gopls_enabled = 0
vim.g.go_gopls_gofumpt = 0

-- >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Airline >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
-- Doc: https://github.com/vim-airline/vim-airline
-- Need to set before loading the plugin

-- Using vim.pack to manage plugins
vim.g.airline_extensions = { 'tabline', 'nvimlsp', 'gutentags' }

-- Enable Tab on top
vim.g.airline_extensions_tabline_enabled = 1
vim.g.airline_extensions_tabline_buffer_idx_mode = 1

-- LSP
vim.g.airline_extensions_nvimlsp_enabled = 1
vim.g.airline_extensions_gutentags_enabled = 1

-- >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Plugins >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
vim.pack.add({
  -- Utilities
  'https://github.com/lewis6991/fileline.nvim',
  'https://github.com/ibhagwan/fzf-lua',
  'https://github.com/nvim-tree/nvim-web-devicons',
  'https://github.com/junegunn/vim-peekaboo',
  'https://github.com/tpope/vim-fugitive',
  'https://github.com/tpope/vim-surround',
  'https://github.com/tpope/vim-repeat',

  -- Indentation
  'https://github.com/lukas-reineke/indent-blankline.nvim',

  -- Status bar
  'https://github.com/vim-airline/vim-airline',
  'https://github.com/airblade/vim-gitgutter',

  -- TreeSitter
  'https://github.com/nvim-treesitter/nvim-treesitter',
  'https://github.com/nvim-treesitter/playground',

  -- LSP Client
  'https://github.com/delphinus/cmp-ctags',
  'https://github.com/hrsh7th/cmp-buffer',
  'https://github.com/hrsh7th/cmp-nvim-lsp',
  'https://github.com/hrsh7th/nvim-cmp',
  'https://github.com/neovim/nvim-lspconfig',

  -- Sneak
  'https://github.com/justinmk/vim-sneak',

  -- Copilot
  'https://github.com/github/copilot.vim',

  -- Golang
  'https://github.com/fatih/vim-go',

  -- Neotest
  'https://github.com/nvim-lua/plenary.nvim',
  'https://github.com/nvim-neotest/nvim-nio',
  'https://github.com/nvim-neotest/neotest',
  '~/work/misc/neotest-bazel',

  -- Bazel / Ctags
  'https://github.com/ludovicchabant/vim-gutentags',
  'https://github.com/dhananjaylatkar/cscope_maps.nvim',

  -- Coloring
  'https://github.com/joshdick/onedark.vim',
  'https://github.com/towolf/vim-helm',
})

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
-- remove the default keymaps from https://github.com/neovim/neovim/pull/28650
vim.keymap.del("n", "grn")
vim.keymap.del("n", "grr")
vim.keymap.del({ "v", "n" }, "gra")

vim.lsp.inlay_hint.enable(true)

local function on_list(options)
  vim.fn.setqflist({}, ' ', options)
  if #options.items > 1 then
    vim.cmd("botright cwindow") -- always take full width
  end
  vim.cmd.cfirst()
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
    local opts = { buffer = bufnr, remap = false }
    local client = vim.lsp.get_client_by_id(args.data.client_id)
    if not client then
      vim.notify("lsp client id " .. args.data.client_id .. " not found.", vim.log.levels.WARN)
      return -- Stop
    end

    -- Set buffer-local options
    vim.bo[bufnr].omnifunc = 'v:lua.vim.lsp.omnifunc'
    vim.bo[bufnr].tagfunc = 'v:lua.vim.lsp.tagfunc'
    vim.bo[bufnr].formatexpr = 'v:lua.vim.lsp.formatexpr()'

    -- Keymaps (combining existing and common lsp-zero defaults)
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
      vim.keymap.set("n", "gr", function() vim.lsp.buf.references(nil, { on_list = on_list }) end, opts)
      vim.keymap.set("n", "gR", function()
        vim.cmd.vsplit()
        vim.lsp.buf.references(nil, { on_list = on_list })
      end, opts)
    end
    if client:supports_method('textDocument/definition') then
      vim.keymap.set("n", "gd", function() vim.lsp.buf.definition({ on_list = on_list }) end, opts)
      vim.keymap.set("n", "gD", function()
        vim.cmd.vsplit()
        vim.lsp.buf.definition({ on_list = on_list })
      end, opts)
    end
    vim.keymap.set('n', '<leader>e', vim.diagnostic.open_float, opts)
    vim.keymap.set('n', '<leader>E', vim.diagnostic.setloclist, opts)
    vim.keymap.set('n', ']d', function()
      vim.diagnostic.jump({ count = 1, float = { border = 'rounded' } })
    end, opts)
    vim.keymap.set('n', '[d', function() -- Add jump to previous diagnostic
      vim.diagnostic.jump({ count = -1, float = { border = 'rounded' } })
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
  end,
})


local lspconfig = require 'lspconfig'
lspconfig.gopls.setup {
  settings = {
    gopls = {
      usePlaceholders = true,
      buildFlags = { "-tags=linux,amd64" },
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
        disabled = { "inactive-code" }, -- Disables the inactive code highlighting
      },
    },
  },
}
lspconfig.starpls.setup {}
lspconfig.bazelrc_lsp.setup {}
lspconfig.protols.setup {}
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
vim.g.gutentags_enabled_dirs = { vim.fn.expand('~/work/bazelbuild/bazel') }

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
