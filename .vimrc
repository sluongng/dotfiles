">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Editor Settings >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

set history=900
set number relativenumber
set ruler
set cmdheight=2
set clipboard+=unnamedplus

" Enable syntax highlighting
syntax enable

" Highlight search results
set hlsearch

" Tab as spaces
set expandtab shiftwidth=2 tabstop=2

" No bell on error, dont use swapfile
set noerrorbells novisualbell
set nobackup nowb noswapfile


" Shortcuts
let mapleader = ","
imap jj <esc>


">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Plugins >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
" Doc: https://github.com/junegunn/vim-plug

call plug#begin('~/.local/share/nvim/plugged')

Plug 'scrooloose/nerdtree', { 'on':  'NERDTreeToggle' }
Plug 'Xuyuanp/nerdtree-git-plugin'

Plug 'junegunn/fzf', { 'dir': '~/.fzf', 'do': './install --all' }
Plug 'junegunn/fzf.vim'

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
autocmd bufenter * if (winnr("$") == 1 && exists("b:NERDTree") && b:NERDTree.isTabTree()) | q | endif
let NERDTreeShowHidden=1


">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Coc.Nvim >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
" Doc: https://github.com/neoclide/coc.nvim

"" Extensions
let g:coc_global_extensions = ["coc-json", "coc-java"]

"" Use C-j and C-k to navigate completion suggestions
inoremap <expr> <C-j> pumvisible() ? "\<C-n>" : "\<C-j>"
inoremap <expr> <C-k> pumvisible() ? "\<C-p>" : "\<C-k>"

"" Use Enter to confirm conpletion
inoremap <expr> <cr> pumvisible() ? "\<C-y>" : "\<C-g>u\<CR>"

"" Use <c-space>for trigger completion
inoremap <silent><expr> <c-space> coc#refresh()

"" Goto mapping
nmap <silent> gd <Plug>(coc-definition)
nmap <silent> gi <Plug>(coc-implementation)
nmap <silent> gr <Plug>(coc-references)
nmap <silent> gy <Plug>(coc-type-definition)
nmap <silent> ge <Plug>(coc-diagnostic-next)

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

