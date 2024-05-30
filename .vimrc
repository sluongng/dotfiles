">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Plugins >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
" Doc: https://github.com/junegunn/vim-plug

call plug#begin('~/.local/share/nvim/plugged')

"" Utilities
Plug 'preservim/nerdcommenter'
Plug 'lewis6991/fileline.nvim'

Plug 'junegunn/fzf', { 'dir': '~/.fzf', 'do': './install --all' }
Plug 'junegunn/fzf.vim'
Plug 'junegunn/vim-peekaboo'

Plug 'tpope/vim-fugitive'
Plug 'tpope/vim-surround'
Plug 'tpope/vim-repeat'


Plug 'github/copilot.vim'

"" Indentation
Plug 'lukas-reineke/indent-blankline.nvim', { 'main': 'ibl', 'opts': {} }


"" Status bar
Plug 'vim-airline/vim-airline'
Plug 'airblade/vim-gitgutter', {'branch': 'main'}

"" TreeSitter
Plug 'nvim-treesitter/nvim-treesitter', {'do': ':TSUpdate'}
Plug 'nvim-treesitter/playground'

"" LSP Client
Plug 'neoclide/coc.nvim', {'branch': 'release'}

"" Golang
Plug 'fatih/vim-go'

"" Bazel
"
" Add maktaba and bazel to the runtimepath.
" (The latter must be installed before it can be used.)
Plug 'google/vim-maktaba'
Plug 'google/vim-codefmt'
Plug 'google/vim-glaive'
Plug 'bazelbuild/vim-bazel'

"" Python
Plug 'numirias/semshi', {'do': ':UpdateRemotePlugins'}

"" Coloring
Plug 'joshdick/onedark.vim', { 'branch': 'main'}

call plug#end()

call glaive#Install()

">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Editor Settings >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

set nocompatible

set ruler
set hidden
set cmdheight=2
set history=9000
set signcolumn=auto
set number relativenumber
set clipboard+=unnamedplus
set scrolloff=5

if has('macunix')
  " No need to set this on MacOS
elseif has('unix')
  " Set clipboard control to xsel on Ubuntu
  let g:clipboard = {
    \  'name': 'xsel',
    \  'copy': {
    \    '+': 'xsel -ib',
    \    '*': 'xsel -ip'
    \  },
    \  'paste': {
    \    '+': 'xsel -ob',
    \    '*': 'xsel -op'
    \  },
    \  'cache_enabled': 1
    \}
endif

" Mouse support
set mouse=a

" show invisible characters
set list
" but only show tabs and trailing whitespace
set listchars=tab:»·,nbsp:+,trail:·,extends:→,precedes:←

" Enable syntax highlighting
set syntax=enable

" Highlight search results
" Use Ctrl-L to clear search highlighting
set hlsearch
nnoremap <silent> <Esc><Esc> :nohlsearch<CR>
nnoremap <silent> <C-l> :nohl<CR><C-l>

" Tab as spaces
set expandtab shiftwidth=2 tabstop=2

" No bell on error, dont use swapfile
set noerrorbells novisualbell
set nobackup nowritebackup noswapfile

" Indentation
"" Retain indentation on next line
set autoindent
"" Increase/decrease indentation automatically
set smartindent

" Search default
set ignorecase
set smartcase

" Shortcuts
let mapleader = ";"

" Fast way to escape
imap jj <Esc>

" Put the new window below
set splitbelow
" Put the new window right
set splitright

" Don't use Ex mode
map Q <Nop>

" Color
let $NVIM_TUI_ENABLE_TRUE_COLOR=1
colorscheme onedark

" Work around for onedark theme does not have
" color group dedicated for CocNvim
hi link CocMenuSel Search

let g:semshi#filetypes = ["python", "bzl"]

">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Coc.Nvim >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
" Doc: https://github.com/neoclide/coc.nvim

"" Extensions
let g:coc_global_extensions = [
  \"coc-vimlsp",
  \"coc-json",
  \"coc-java",
  \"coc-xml",
  \"coc-snippets",
  \"coc-rust-analyzer",
\]

" Improve default update time wait from 4000(4 seconds)
" :help CursorHold
set updatetime=100
" Highlight text on idle
autocmd CursorHold * silent call CocActionAsync('highlight')

"" Use Tab instead of C-j to move during snippet
let g:coc_snippet_next = '<tab>'

"" Use C-j and C-k to navigate completion suggestions
inoremap <expr> <C-j> coc#pum#visible() ? coc#pum#next(1) : "\<C-j>"
inoremap <expr> <C-k> coc#pum#visible() ? coc#pum#prev(1) : "\<C-k>"

"" Use Enter to confirm first conpletion
inoremap <expr> <cr> coc#pum#visible() ? coc#_select_confirm() : "\<CR>"

"" Use <c-space>for trigger completion
inoremap <silent><expr> <c-space> coc#refresh()

"" Goto mapping
nmap <silent> gd <Plug>(coc-definition)
nmap <silent> gi <Plug>(coc-implementation)
nmap <silent> gr <Plug>(coc-references)
nmap <silent> gy <Plug>(coc-type-definition)
nmap <silent> ge <Plug>(coc-diagnostic-next)

"" Show documentation in preview window
nnoremap <silent> gk :call <SID>show_documentation()<CR>
function! s:show_documentation()
  if (index(['vim', 'help'], &filetype) >= 0)
    execute 'h '.expand('<cword>')
  else
    call CocAction('doHover')
  endif
endfunction

"" Auto clode the preview window when completion is done
autocmd! CompleteDone * if pumvisible() == 0 | pclose | endif

"" Refactoring
nmap <leader>rn <Plug>(coc-rename)
nmap <leader>qf <Plug>(coc-fix-current)

"" Use `:Format` to format current buffer
command! -nargs=0 Format :call CocAction('format')

"" Use `:Fold` to fold current buffer
command! -nargs=? Fold :call     CocAction('fold', <f-args>)

"" Use `:OR` for organize import of current buffer
command! -nargs=0 OR   :call     CocAction('runCommand', 'editor.action.organizeImport') 


">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> fzf.vim >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
" Doc: https://github.com/junegunn/fzf.vim

" Make fzf use neovim floating window
if has('nvim')
  function! FloatingFZF(width, height, border_highlight)
    function! s:create_float(hl, opts)
      let buf = nvim_create_buf(v:false, v:true)
      let opts = extend({'relative': 'editor', 'style': 'minimal'}, a:opts)
      let win = nvim_open_win(buf, v:true, opts)
      call setwinvar(win, '&winhighlight', 'NormalFloat:'.a:hl)
      call setwinvar(win, '&colorcolumn', '')
      return buf
    endfunction

    " Size and position
    let width = float2nr(&columns * a:width)
    let height = float2nr(&lines * a:height)
    let row = float2nr((&lines - height) / 2)
    let col = float2nr((&columns - width) / 2)

    " Border
    let top = '╭' . repeat('─', width - 2) . '╮'
    let mid = '│' . repeat(' ', width - 2) . '│'
    let bot = '╰' . repeat('─', width - 2) . '╯'
    let border = [top] + repeat([mid], height - 2) + [bot]

    " Draw frame
    let s:frame = s:create_float(a:border_highlight, {'row': row, 'col': col, 'width': width, 'height': height})
    call nvim_buf_set_lines(s:frame, 0, -1, v:true, border)

    " Draw viewport
    call s:create_float('Normal', {'row': row + 1, 'col': col + 2, 'width': width - 4, 'height': height - 2})
    autocmd BufWipeout <buffer> execute 'bwipeout' s:frame
  endfunction

  let $FZF_PREVIEW_COMMAND="bat --style=numbers --color=always {}"
  let g:fzf_layout = { 'window': 'call FloatingFZF(0.9, 0.6, "Comment")' }
endif

" Some QoL shortcuts
nnoremap <leader>a :Commands<CR>
nnoremap <leader>b :Buffers<CR>
nnoremap <leader>f :FZF<CR>
nnoremap <leader>r :Rg<CR>


">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Airline >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
" Doc: https://github.com/vim-airline/vim-airline


"" Enable Tab on top
let g:airline#extensions#tabline#enabled = 1
let g:airline#extensions#tabline#buffer_idx_mode = 1
nmap <leader>1 <Plug>AirlineSelectTab1
nmap <leader>2 <Plug>AirlineSelectTab2
nmap <leader>3 <Plug>AirlineSelectTab3
nmap <leader>4 <Plug>AirlineSelectTab4
nmap <leader>5 <Plug>AirlineSelectTab5
nmap <leader>6 <Plug>AirlineSelectTab6
nmap <leader>7 <Plug>AirlineSelectTab7
nmap <leader>8 <Plug>AirlineSelectTab8
nmap <leader>9 <Plug>AirlineSelectTab9
nmap <leader>- <Plug>AirlineSelectPrevTab
nmap <leader>+ <Plug>AirlineSelectNextTab

"" Extention: CocNvim
let g:airline#extensions#coc#enabled = 1
let airline#extensions#coc#show_coc_status = 0
let airline#extensions#coc#stl_format_err = '%E{[%e(#%fe)]}'
let airline#extensions#coc#stl_format_warn = '%W{[%w(#%fw)]}'

">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> TreeSitter >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
lua <<EOF
require'nvim-treesitter.configs'.setup {
  ensure_installed = "all",
  -- Install parsers synchronously (only applied to `ensure_installed`)
  sync_install = false,
  highlight = {
    enable = true, -- false will disable the whole extension
  },
  incremental_selection = {
    enable = true,
    keymaps = {
      init_selection = "<A-L>", -- set to `false` to disable one of the mappings
      scope_incremental = false,
      node_incremental = "<A-L>",
      node_decremental = "<A-H>",
    },
  },
  playground = {
    enable = true,
    disable = {},
    updatetime = 25, -- Debounced time for highlighting nodes in the playground from source code
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
    lint_events = {"BufWrite", "CursorHold"},
  }
}
EOF

">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Language Settings >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

au FileType bzl set noexpandtab
au FileType bzl set shiftwidth=4
au FileType bzl set softtabstop=4
au FileType bzl set tabstop=4

" File Type handling
" Doc: ':h filetype'
filetype plugin on

" Golang
"   Doc: https://github.com/fatih/vim-go/blob/master/doc/vim-go.txt 
"        or ':h go-syntax'
"" Indentation
au FileType go set noexpandtab
au FileType go set shiftwidth=2
au FileType go set softtabstop=2
au FileType go set tabstop=2
au FileType go let g:editorconfig = v:false
"" Syntax Highlight
let g:go_highlight_functions = 1
let g:go_highlight_function_parameters = 1
let g:go_highlight_function_calls = 1
"" Syntax Highlight
let g:go_highlight_types = 1
let g:go_highlight_extra_types = 1
"" Syntax Highlight
let g:go_highlight_fields = 1
let g:go_highlight_methods = 1
let g:go_highlight_operators = 1
let g:go_highlight_structs = 1
let g:go_highlight_generate_tags = 1
let g:go_highlight_format_strings = 1
let g:go_highlight_variable_declarations = 1
let g:go_highlight_variable_assignments = 1
"" Syntax Highlight
let g:go_highlight_build_constraints = 1
let g:go_highlight_array_whitespace_error = 1
let g:go_highlight_chan_whitespace_error = 1
"" Highlight variable with same name
let g:go_auto_sameids=0
"" Disbale vim-go :GoDef to use gopls + coc.nvim 
let g:go_def_mapping_enabled = 0
"" Format with gopls
let g:go_fmt_command="gopls"
let g:go_gopls_enabled=0
let g:go_gopls_gofumpt=0

" Markdown
augroup Markdown
  autocmd!
  autocmd FileType markdown set wrap
augroup END

" Java
"" Indentation
au FileType java set expandtab
au FileType java set shiftwidth=2
au FileType java set softtabstop=2
au FileType java set tabstop=2

" Rust
let g:rustfmt_options = '--edition 2021'

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

augroup autoformat_settings
  autocmd FileType bzl AutoFormatBuffer buildifier
  autocmd FileType c,cpp,arduino AutoFormatBuffer clang-format
  autocmd FileType javascript,vue AutoFormatBuffer prettier
  autocmd FileType dart AutoFormatBuffer dartfmt
  autocmd FileType go AutoFormatBuffer gofmt
  autocmd FileType gn AutoFormatBuffer gn
  autocmd FileType html,css,sass,scss,less,json AutoFormatBuffer js-beautify
  " autocmd FileType java AutoFormatBuffer google-java-format
  autocmd FileType python AutoFormatBuffer black
  autocmd FileType rust AutoFormatBuffer rustfmt
augroup END
