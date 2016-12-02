#TODO add warning about overwrite before copying to home directory!

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Copying files from $DIR/aliases to $HOME/aliases"
yes | cp -aR $DIR/aliases/. $HOME/aliases/

echo "Copying files from $DIR/dotfiles to $HOME"
yes | cp -aR $DIR/dotfiles/. ~/

echo "Copying files from $DIR/scripts to $HOME/scripts"
yes | cp -aR $DIR/scripts/. $HOME/scripts

echo "Copying $DIR/.bashrc to $HOME/.bashrc"
cp $DIR/.bashrc ~/.bashrc;

echo "Copying $DIR/configurations/i3/* to $HOME/.i3/"
cp $DIR/configurations/i3/* $HOME/.i3
