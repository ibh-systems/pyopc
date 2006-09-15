# Makefile fuer TeX 
#
# Author: Hermann Himmelbauer
# Date: 29. Sept. 1996
# Modified: 29. Sept 1996
#
# define source
#

MAINFILE = main
DVIFILE = PyOPC
OPTS = 

#
# default rules
#
all:: dvi

everything:: dvi ps pdf tty

dvi:: ${MAINFILE}.tex
	latex ${OPTS} ${MAINFILE}.tex;latex ${OPTS} ${MAINFILE}.tex;\
        mv ${MAINFILE}.dvi ${DVIFILE}.dvi; cp ${DVIFILE}.dvi ..

ps:: ${DVIFILE}.dvi
	dvips ${DVIFILE}.dvi -o ../${DVIFILE}.ps

html:: ${MAINFILE}.tex
	latex2html -antialias_text -antialias -white -local_icons ${MAINFILE}.tex;\
        rm ../html/*;\
        mv main/*.html ../html;\
        mv main/*.png ../html


pdf:: ${DVIFILE}.dvi
	dvipdf ${DVIFILE}.dvi ../${DVIFILE}.pdf

tty:: ${DVIFILE}.dvi
	dvi2tty ${DVIFILE}.dvi > ../${DVIFILE}.txt

clean:: 
	rm *.rtf *.ps *.dvi *.html *.aux *.pdf *.log *.toc

