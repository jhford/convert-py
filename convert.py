#!/usr/bin/env python
import os
import sys
import subprocess as sp
import tempfile
import imghdr
import logging

# I don't want to have to run with PYTHONPATH
sys.path.append(os.path.abspath(os.path.split(__file__.rstrip(os.sep))[0]))
import util
import mp

class EncodingFailure(Exception): pass

class FlacToMP3Job(mp.Job):
    flac_bin = 'flac'
    metaflac_bin = 'metaflac'
    lame_bin = 'lame'
    eyeD3_bin = 'eyeD3'

    def __init__(self, infile, settings=['-V2']):
        mp.Job.__init__(self)
        self.infile = infile
        self.settings = settings
        self.log = logging.getLogger('convert')

    def run(self):
        important_tags = ('title', 'artist', 'album', 'tracknumber', 'discnumber')
        # Figure out the metadata.
        data = {}
        self.log.info('BEGIN METADATA "%s"', os.path.basename(self.infile))
        for i in important_tags:
            output = unicode(sp.check_output([self.metaflac_bin, '--no-utf8-convert', '--show-tag=%s' % i,
                                              self.infile]), encoding='utf-8')
            if '=' in output:
                data[i] = output[output.index('=')+1:].strip()
            else:
                data[i] = output.strip()

        # This exception handler is ugly but I don't know a good
        # way to check if a flac file has a picture without lots
        # of code.  Laziness abounds
        try:
            # Assuming jpg file is really lame
            tmppicfd, tmppicfile = tempfile.mkstemp(prefix='flacpic_', suffix='.jpg')
            os.close(tmppicfd)
            os.unlink(tmppicfile)
            output = sp.check_output([self.metaflac_bin,
                           '--export-picture-to=%s'%tmppicfile,
                           self.infile])
            picture = tmppicfile
        except sp.CalledProcessError:
            self.log.debug('could not extract picture from %s', self.infile)
            picture = None
        self.log.info('END METADATA "%s"', os.path.basename(self.infile))

        # Decode flac file to temporary wav file
        tmpfd, tmpfile = tempfile.mkstemp(prefix='flacinput_', suffix='.wav')
        os.close(tmpfd)
        os.unlink(tmpfile)
        self.log.info('BEGIN DECODE "%s"', os.path.basename(self.infile))
        sp.check_call([self.flac_bin, '--silent', '--decode', self.infile, '--output-name=%s'%tmpfile])
        self.log.info('END DECODE "%s"', os.path.basename(self.infile))

        # Encode wav into mp3
        output_file = os.path.join(u'output', data['artist'], data['album'],
                    u'%s %s.mp3' % (data['tracknumber'], data['title']))
        try:
            os.makedirs(os.path.dirname(output_file))
        except OSError:
            pass # TODO: do something smarter here
        self.log.info('BEGIN ENCODE "%s"', os.path.basename(self.infile))
        sp.check_call([self.lame_bin, '--quiet'] + self.settings + [tmpfile, output_file])
        self.log.info('END ENCODE "%s"', os.path.basename(self.infile))

        # Set ID3 tags
        self.log.info('BEGIN ID3 "%s"', os.path.basename(self.infile))
        devnull = os.open(os.devnull, os.O_WRONLY)
        sp.check_call([self.eyeD3_bin, u'--to-v2.4',
                       u'--artist=%s' % data['artist'],
                       u'--album=%s' % data['album'],
                       u'--title=%s' % data['title'],
                       u'--track=%s' % data['tracknumber'],
                       u'--set-encoding=utf8',
                       output_file],
                       stdout=devnull,
                       stderr=sp.STDOUT)
        if picture:
            sp.check_call([self.eyeD3_bin, u'--add-image=%s:FRONT_COVER' % picture,
                           output_file],
                           stdout=devnull,
                           stderr=sp.STDOUT)
        os.close(devnull)
        self.log.info('END ID3 "%s"', os.path.basename(self.infile))
        os.unlink(tmpfile)
        if picture:
            os.unlink(tmppicfile)


def main():
    log = util.setup_logging('convert', volume=11)
    log.info("Converting some files for you")

    flacs=[]
    for i in sys.argv[1:]:
        with open(i) as f:
            flacs.extend([x.strip() for x in f.readlines()])
    jobs = []
    for flac in flacs:
        jobs.append(FlacToMP3Job(flac))
    mp.ThreadPool(jobs).run_jobs()


if __name__ == "__main__":
    main()
