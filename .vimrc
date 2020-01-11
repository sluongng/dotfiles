">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Plugins >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
" Doc: https://github.com/junegunn/vim-plug

call plug#begin('~/.local/share/nvim/plugged')

Plug 'scrooloose/nerdtree', { 'on':  'NERDTreeToggle' }
Plug 'Xuyuanp/nerdtree-git-plugin'

Plug 'junegunn/fzf', { 'dir': '~/.fzf', 'do': './install --all' }
Plug 'junegunn/fzf.vim'
Plug 'junegunn/vim-peekaboo'

" Theme / Look
Plug 'joshdick/onedark.vim'
Plug 'luochen1990/rainbow'

" Utils
Plug 'tpope/vim-fugitive'
Plug 'tpope/vim-surround'

" Bottom bar
Plug 'vim-airline/vim-airline'
Plug 'airblade/vim-gitgutter'

" LSP client
Plug 'neoclide/coc.nvim', {'branch': 'release'}

" Golang
Plug 'fatih/vim-go'

" Python
Plug 'numirias/semshi', {'do': ':UpdateRemotePlugins'}

" Multilanguage
Plug 'sheerun/vim-polyglot'

call plug#end()


">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Editor Settings >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

set nocompatible

set ruler
set hidden
set cmdheight=2
set history=9000
set signcolumn=auto
set number relativenumber
set clipboard+=unnamedplus

set scrolloff=2

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

" Shortcuts
let mapleader = ","

" Fast way to escape
imap jj <Esc>


">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Color / Theme >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

" Enable syntax highlighting
set syntax=on

let g:onedark_terminal_italics = 1
if (has("autocmd") && !has("gui_running"))
  augroup colorset
    autocmd!
    let s:white = { "gui": "#ABB2BF", "cterm": "145", "cterm16" : "7" }
    autocmd ColorScheme * call onedark#set_highlight("Normal", { "fg": s:white }) " `bg` will not be styled since there is no `bg` setting
  augroup END
endif
colorscheme onedark

let g:rainbow_active = 1


">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> NERDTree >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
" Doc: https://github.com/scrooloose/nerdtree

map <C-n> :NERDTreeToggle<CR>

"" Open NERDTree when no file was specified
autocmd StdinReadPre * let s:std_in=1
autocmd VimEnter * if argc() == 1 && isdirectory(argv()[0]) && !exists("s:std_in") | exe 'NERDTree' argv()[0] | wincmd p | ene | exe 'cd '.argv()[0] | endif

"" Close when NERDTree is the only window left
autocmd bufenter * if (winnr("$") == 1 && exists("b:NERDTree") && b:NERDTree.isTabTree()) | q | endif

let NERDTreeShowHidden=1


">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Coc.Nvim >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
" Doc: https://github.com/neoclide/coc.nvim

"" Extensions
let g:coc_global_extensions = [
  \"coc-vimlsp", 
  \"coc-json", 
  \"coc-java", 
  \"coc-xml", 
  \"coc-snippets",
  \"coc-pairs", 
  \"coc-git", 
  \"coc-tabnine", 
  \"coc-rls", 
\]

" Improve default update time wait from 4000(4 seconds)
" :help CursorHold
set updatetime=200
" Highlight text on idle
autocmd CursorHold * silent call CocActionAsync('highlight')

" Show docs if idle more than 2 seconds
function! MyStopInsert(timerid)
    " echom "Executed timer " . a:timerid
    " Fo some reason stopinsert doesn't exit insert mode immediately
    " execute("stopinsert")
    call CocActionAsync('doHover')
    call MyStopTimer()
endfun
function! MyStartTimer()
    call MyStopTimer()
    let b:mytimer = timer_start(2000, "MyStopInsert")
    " echom "Started timer " . b:mytimer
endfun
function! MyStopTimer()
    if exists("b:mytimer")
        " echom "Stopping timer " . b:mytimer
        call timer_stop(b:mytimer)
        unlet b:mytimer
    endif
endfun
augroup MyEscTimer
    autocmd!
    autocmd CursorHold * call MyStartTimer()
    autocmd CursorMoved * call MyStopTimer()
augroup end

"" Use Tab instead of C-j to move during snippet
let g:coc_snippet_next = '<tab>'

"" Use C-j and C-k to navigate completion suggestions
inoremap <expr> <C-j> pumvisible() ? "\<C-n>" : "\<C-j>"
inoremap <expr> <C-k> pumvisible() ? "\<C-p>" : "\<C-k>"

"" Use Enter to confirm first conpletion
inoremap <silent><expr> <cr> pumvisible() ? coc#_select_confirm() : "\<C-g>u\<CR>"

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
  "" Make the window a bit easier to see on dark background
  let $FZF_DEFAULT_OPTS .= ' --border'

  function! FloatingFZF()
    let width = float2nr(&columns * 0.8)
    let height = float2nr(&lines * 0.6)
    let opts = {
          \ 'relative': 'editor',
          \ 'row': (&lines - height) / 2,
          \ 'col': (&columns - width) / 2,
          \ 'width': width,
          \ 'height': height,
          \ 'style': 'minimal'
          \ }
    let buf = nvim_create_buf(v:false, v:true)
    let win = nvim_open_win(buf, v:true, opts)
    call setwinvar(win, '&winhl', 'NormalFloat:Error')
  endfunction

  let g:fzf_layout = { 'window': 'call FloatingFZF()' }
endif

" Some QoL shortcuts
nnoremap <leader>a :Commands<CR>
nnoremap <leader>f :FZF<CR>


">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Airline >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
" Doc: https://github.com/vim-airline/vim-airline

"" Enable Extensions
let g:airline#extensions#coc#enabled = 1

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
let airline#extensions#coc#stl_format_err = '%E{[%e(#%fe)]}'
let airline#extensions#coc#stl_format_warn = '%W{[%w(#%fw)]}'


">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Language Settings >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


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
let g:go_auto_sameids = 1
"" Disbale vim-go :GoDef to use gopls + coc.nvim 
let g:go_def_mapping_enabled = 0

" Markdown
augroup Markdown
  autocmd!
  autocmd FileType markdown set wrap
augroup END

" Java
"" Indentation
au FileType java set noexpandtab
au FileType java set shiftwidth=4
au FileType java set softtabstop=4
au FileType java set tabstop=4

" Rust
let g:rustfmt_options = '--edition 2018'

" Kotlin
" TODO: WIP

" JavaScript
" TODO: WIP

" TypeScript
" TODO: WIP

