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


SRC_DIR=$DIR/dotfiles/i3/
DEST_DIR=$HOME/.i3/
echo "Copying $SRC_DIR to $DEST_DIR"
cp $SRC_DIR/* $DEST_DIR


##copy workplace-specific aliases
SRC_DIR=$DIR/workplace-specific/
DEST_DIR=$HOME/
echo "Copying workplace-specific aliases..."
echo "Copying $SRC_DIR to $HOME/"

test -d "$DEST_DIR" || mkdir -p "$DEST_DIR" && yes | cp -aR $SRC_DIR $DEST_DIR

echo Sourcing files from $HOME/aliases;
for f in $HOME/aliases/*.sh; do
  echo Sourcing file $f
  . "$f"
done
echo Done sourcing files from ~/aliases;

echo "Searching for .source-this files and sourcing them..."
matched_dirs=$(find $HOME/workplace-specific/ -name .source-this -printf "%h\n")
for d in $matched_dirs; do
  echo Sourcing files from $d
  for f in $(find $d -maxdepth 1 -iname  "*.sh"); do
    echo Sourcing file $f
    . "$f"
  done
done
