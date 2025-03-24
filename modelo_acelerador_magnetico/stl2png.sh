for i in *.stl; do
  T=__tmp__$i
  b=`basename $i`
  echo import\(\"$i\"\)\; >$T
  /usr/bin/openscad -o $b.png --imgsize=1200,800 $T
  rm $T
done
