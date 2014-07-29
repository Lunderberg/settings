#!/usr/bin/env python

"""
Prints out level schemes to be used in latex.

% Add the following lines to your latex file to use the levelscheme environment.
% When compiling, use the --shell-escape flag.
\usepackage{fancyvrb}
\usepackage{tikz}
\newenvironment{levelscheme}
  {\VerbatimOut{\jobname.stdin}}
  {\endVerbatimOut
    \input{|"levelscheme.py < \jobname.stdin"}
  }


"""

import sys

def options(strings,prev=None):
    if prev is None:
        output = {}
    else:
        output = prev.copy()
    for s in strings:
        key = s[:s.index('=')]
        value = s[s.index('=')+1:]
        if key in output:
            output[key] = output[key] + ',' + value
        else:
            output[key] = value
    return output

class poscounter(object):
    def __init__(self,x=0):
        self.x = x
        self.intervals = []
    def next_pos(self,initial,final):
        for old_initial,old_final in self.intervals:
            above = (initial>=old_initial and initial>=old_final and
                     final>=old_initial and final>=old_final)
            below = (initial<=old_initial and initial<=old_final and
                     final<=old_initial and final<=old_final)
            if not (above or below):
                self.intervals = []
                self.x += 0.6
                break
        self.intervals.append((initial,final))
        return self.x


class LevelScheme(object):
    def __init__(self):
        self.schemes = []
        self.curr_levels = []
        self.curr_gammas = []
        self.defaults = {}
    def ProcessLine(self,line):
        command = line.split()
        if not command:
            return
        if command[0]=='level':
            newlevel = [float(command[1]),options(command[2:],prev=self.defaults)]
            self.curr_levels.append(newlevel)
        elif command[0]=='gamma':
            newgamma = [float(command[1]),float(command[2]),
                        options(command[3:],prev=self.defaults)]
            self.curr_gammas.append(newgamma)
        elif command[0]=='sep':
            self.schemes.append((self.curr_levels,self.curr_gammas))
            self.curr_levels = []
            self.curr_gammas = []
        elif command[0]=='opt':
            self.defaults.update(options(command[1:]))
    def DrawGammaSet(self,levels,gammas,xstart):
        #Draw each gamma
        counter = poscounter(xstart)
        for initial,final,opt in gammas:
            stropt = []
            if 'color' in opt:
                stropt.append('color={}'.format(opt['color']))
            if 'opt' in opt:
                stropt.append(opt['opt'])
            stropt = ',' + ','.join(stropt) if stropt else ''
            xpos = counter.next_pos(initial,final)
            print r"\draw[line width=2,-> {opt}] ({x},{ini}) -- coordinate (mid) ({x},{fin});".format(
                ini=initial,fin=final,opt=stropt,x=xpos)
            if 'label' in opt:
                print r'\node[rotate=90,above] at (mid) {{{label}}};'.format(label=opt['label'])

        #Draw each level
        xfinal = max(xstart+3,counter.x)
        ydiff = 0.3
        ylabel = -ydiff
        for energy,opt in sorted(levels):
            stropt = []
            if 'color' in opt:
                stropt.append('color={}'.format(opt['color']))
            if 'opt' in opt:
                stropt.append(opt['opt'])
            stropt = ','.join(stropt)
            label = ''
            if 'label' in opt:
                ylabel = max(energy,ylabel+ydiff)
                label = '-- ({xf}+0.5,{ylabel}) -- ({xf}+1.0,{ylabel}) node[right] {{{label}}}'.format(
                    xf=xfinal,ylabel=ylabel,label=opt['label'])
            print r"\draw[{opt}] ({xi},{en}) -- ({xf},{en}) {label};".format(
                en=energy,opt=stropt,xi=xstart,xf=xfinal,label=label)

        return xfinal + 3.0

    def Print(self):
        #Environment begin
        print r"\begin{tikzpicture}[yscale=2]"

        #y-axis
        print r"""\draw (0,0) -- coordinate (y-axis-mid) (0,4.0);
                   \foreach \y in {0,0.5,...,4.0}
                       \draw (1pt,\y) -- (-3pt,\y) node[anchor=east] {\y};
                  \node[rotate=90,above=0.8cm] at (y-axis-mid) {Energy (MeV)};"""

        #All the gammas
        xval = 1.0
        for levels,gammas in self.schemes:
            xval = self.DrawGammaSet(levels,gammas,xval)
        xval = self.DrawGammaSet(self.curr_levels,self.curr_gammas,xval)



        #Environment end
        print r"\end{tikzpicture}"


if __name__=='__main__':
    scheme = LevelScheme()
    for line in sys.stdin:
        scheme.ProcessLine(line)
    scheme.Print()
