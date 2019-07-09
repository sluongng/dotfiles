" Editor Settings
set history=900
set number relativenumber
set ruler
set cmdheight=2
set clipboard+=unnamedplus

syntax enable

set hlsearch

set noerrorbells novisualbell

set nobackup nowb noswapfile

set shiftwidth=2
set tabstop=2


" Shortcuts
imap jj <esc>
let mapleader = ","


" Plugins
call plug#begin('~/.local/share/nvim/plugged')

Plug 'scrooloose/nerdtree', { 'on':  'NERDTreeToggle' }

Plug 'junegunn/fzf', { 'dir': '~/.fzf', 'do': './install --all' }

Plug 'tpope/vim-fugitive'
Plug 'tpope/vim-surround'

Plug 'vim-airline/vim-airline'
Plug 'airblade/vim-gitgutter'

Plug 'fatih/vim-go'

Plug 'neoclide/coc.nvim', {'branch': 'release'}

call plug#end()
