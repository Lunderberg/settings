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
        self.input = []
        self.yscale = 2
        self.xscale = 1

    def ProcessLine(self,line):
        self.input.append(line)
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
        elif command[0]=='xscale':
            self.xscale = float(command[1])
        elif command[0]=='yscale':
            self.yscale = float(command[1])

    def DrawGammaSet(self,levels,gammas,xstart):
        output = []

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
            output.append(r"\draw[line width=2,-> {opt}] ({x},{ini}) -- coordinate (mid) ({x},{fin});".format(
                    ini=initial,fin=final,opt=stropt,x=xpos))
            if 'label' in opt:
                output.append(r'\node[rotate=90,right={offset}cm,above] at (mid) {{{label}}};'.format(
                        label=opt['label'],
                        offset=float(opt['offset'])/1000.0 if 'offset' in opt else 0.0))

        #Draw each level
        xfinal = max(xstart+3,counter.x)
        ydiff = 0.6/self.yscale
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
            output.append(r"\draw[{opt}] ({xi},{en}) -- ({xf},{en}) {label};".format(
                    en=energy,opt=stropt,xi=xstart,xf=xfinal,label=label))

        return xfinal + 3.0, '\n'.join(output)

    def MaxLevel(self):
        if self.curr_levels:
            max_current = max(level[0] for level in self.curr_levels)
        else:
            max_current = -1e10
        if self.schemes:
            max_prev = max(level[0] for levels,gammas in self.schemes for level in levels)
        else:
            max_prev = -1e10
        return max(max_current,max_prev)

    def OutputString(self):
        output = []
        #Environment begin
        output.append(r"\begin{{tikzpicture}}[xscale={xscale},yscale={yscale}]".format(xscale=self.xscale,
                                                                                       yscale=self.yscale))

        #y-axis
        ymax = self.MaxLevel()
        ymax = 0.5 * (int(ymax/0.5)+1)
        output.append(r"""\draw (0,0) -- coordinate (y-axis-mid) (0,{ymax});
                            \foreach \y in {{0,0.5,...,{ymax}}}
                            \draw (1pt,\y) -- (-3pt,\y) node[anchor=east] {{\y}};
                         \node[rotate=90,above=0.8cm] at (y-axis-mid) {{Energy (MeV)}};""".format(
                ymax=ymax))

        #All the gammas
        xval = 1.0
        for levels,gammas in self.schemes:
            xval,new_lines = self.DrawGammaSet(levels,gammas,xval)
            output.append(new_lines)
        xval,new_lines = self.DrawGammaSet(self.curr_levels,self.curr_gammas,xval)
        output.append(new_lines)

        #Environment end
        output.append(r"\end{tikzpicture}")

        return '\n'.join(output)

    def Print(self):
        sys.stderr.write('-----------------------------------\n')
        sys.stderr.write('----------------Input--------------\n')
        sys.stderr.write(''.join(self.input))
        sys.stderr.write('-----------------------------------\n')
        output = self.OutputString()
        sys.stderr.write('----------------Output--------------\n')
        sys.stderr.write(output + '\n')
        sys.stderr.write('-----------------------------------\n')

        print output




if __name__=='__main__':
    scheme = LevelScheme()
    for line in sys.stdin:
        scheme.ProcessLine(line)
    scheme.Print()
