">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Editor Settings >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

set nocompatible

set ruler
set hidden
set cmdheight=2
set history=9000
set number relativenumber
set clipboard+=unnamedplus

set scrolloff=2

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

" Shortcuts
let mapleader = ","

" Fast way to escape
imap jj <Esc>


">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Plugins >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
" Doc: https://github.com/junegunn/vim-plug

call plug#begin('~/.local/share/nvim/plugged')

Plug 'scrooloose/nerdtree', { 'on':  'NERDTreeToggle' }
Plug 'Xuyuanp/nerdtree-git-plugin'

Plug 'junegunn/fzf', { 'dir': '~/.fzf', 'do': './install --all' }
Plug 'junegunn/fzf.vim'
Plug 'junegunn/vim-peekaboo'

Plug 'tpope/vim-fugitive'
Plug 'tpope/vim-surround'

Plug 'vim-airline/vim-airline'
Plug 'airblade/vim-gitgutter'

Plug 'fatih/vim-go'

Plug 'neoclide/coc.nvim', {'branch': 'release'}

call plug#end()


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

let g:go_highlight_types = 1
let g:go_highlight_extra_types = 1

let g:go_highlight_fields = 1
let g:go_highlight_methods = 1
let g:go_highlight_operators = 1
let g:go_highlight_structs = 1
let g:go_highlight_generate_tags = 1
let g:go_highlight_format_strings = 1
let g:go_highlight_variable_declarations = 1
let g:go_highlight_variable_assignments = 1

let g:go_highlight_build_constraints = 1
let g:go_highlight_array_whitespace_error = 1
let g:go_highlight_chan_whitespace_error = 1

"" Highlight variable with same name
let g:go_auto_sameids = 1

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


" Kotlin
" TODO: WIP


" JS
" TODO: WIP


" TypeScript
" TODO: WIP

