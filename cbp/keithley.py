import optparse
import time

import numpy as np
import visa

import cbp.monochromater
import cbp.shutter


def parse_commandline():
    """
    Parse the options given on the command-line.
    """
    parser = optparse.OptionParser()

    parser.add_option("--doKeithley", action="store_true", default=False)
    parser.add_option("--doSingle", action="store_true", default=False)
    parser.add_option("--doReset", action="store_true", default=False)
    parser.add_option("--doShutter", action="store_true", default=True)
    parser.add_option("-t","--analysisType", default="duration")
    parser.add_option("-m","--mode", default='char')
    parser.add_option("-d","--duration", default=1, type=int)
    parser.add_option("-p","--photons", default=100000, type=int)
    parser.add_option("-q","--charge", default=10**-6, type=float)
    parser.add_option("-w","--wavelength", default=550, type=int)
    parser.add_option("-f", "--photonFile", default='/home/pi/CBP/keithley/test.dat')

    opts, args = parser.parse_args()

    return opts


class Keithley:
    def __init__(self, rm=None, resnum=None, mode='curr', nplc=1, doReset=False):
        if rm is not None and resnum is not None:
            self.rm = rm
            if resnum == 0:
                devtty = 'ASRL/dev/ttyUSB.KEITHLEY1::INSTR'
            elif resnum == 1:
                devtty = 'ASRL/dev/ttyUSB.KEITHLEY2::INSTR'
            else:
                devtty = rm.list_resources()[resnum]

            self.ins = self.rm.open_resource(devtty)
        else:
            self.rm = visa.ResourceManager('@py')
            self.ins = self.rm.open_resource(self.rm.list_resources()[0])
        self.ins.write_termination = '\n'
        self.ins.read_termination = '\n'
        self.ins.timeout = 5000
        self.ins.query_delay = 0.0

        # ins.write('SYST:ZCH OFF')  #see page 2-2
        # ins.write('SYST:AZER:STAT OFF') #see page 2-13+
        # self.selectmode(mode,nplc=nplc)
        # self.ins.write('CURR:RANG:AUTO ON')
        # self.ins.write('CHAR:RANG:AUTO ON')
        # self.ins.write('VOLT:RANG:AUTO ON')
        self.dispon(True)

        if doReset:
            self.ins.write('*RST')
            self.ins.write('INIT')
        self.selectmode(mode, nplc=nplc)

        self.ins.write('SYST:ZCH ON')
        self.ins.write('SYST:ZCOR ON')
        self.ins.write('SYST:ZCH OFF')
        self.ins.write('SYST:ZCOR OFF')

    def selectmode(self, mode, nplc):
        assert mode.lower() in ['volt', 'char', 'curr', 'res'], "No mode %s" % mode.lower()
        assert type(nplc) == type(1)  # assert that nplc is an int
        # self.ins.write('CONF:%s' % mode.upper())
        # self.ins.write('SENS:%s:NPLC %d' %(mode.upper(),nplc))
        self.ins.write("FUNC '%s'" % (mode.upper()))

    def dispon(self, on):
        if on:
            self.ins.write('DISP:ENAB 1')
        else:
            self.ins.write('DISP:ENAB 0')

    def getread(self):
        '''Array returned is of the form
            [READING, TIME, STATUS]
            Where status is defined in the manual via bitmasks
        '''
        return np.array(self.ins.query('READ?').split(',')).astype(np.float)

    def getquery(self, query):
        return self.ins.query(query)

    def close(self):
        self.ins.close()
        self.rm.close()


def get_keithley(rm, duration=1, photons=100000, charge=10**-6, wavelength=550, mode='curr',
                 analysisType='duration', doSingle=False, doReset=True, photonFile='test.dat',
                 doShutter=True):

    if doSingle:
        # QE for NIST and Thorlabs
        filename = '../input/NIST_PD.txt'
        data_out = np.loadtxt(filename)
        QE_NIST_PD = np.interp(wavelength,data_out[:,0],data_out[:,1])
        filename = '../input/NIST_Thorlabs.txt'
        data_out = np.loadtxt(filename)
        QE_Thorlabs_PD = QE_NIST_PD * \
                 np.interp(wavelength,data_out[:,0],data_out[:,1]/data_out[:,2])

        filename = '../input/CBP_throughput.txt'
        data_out = np.loadtxt(filename)
        throughput = np.interp(wavelength,data_out[:,0],data_out[:,1])
        throughput = throughput*1.67 # Vignetting correction

        cbp.monochromater.main(runtype = "monowavelength", val = wavelength)

        if True:
        #try:
            ins1 = Keithley(rm = rm, resnum = 0, mode = mode, doReset = doReset)
            if analysisType == 'duration':
                start_time = time.time()
                elapsed_time = time.time() - start_time

                times = []
                photo1 = []
                totphotons = []

                for ii in xrange(10):
                    thistime = time.time()
                    elapsed_time = thistime - start_time

                    photo = ins1.getread()[0]

                    photo1.append(photo)
                    times.append(thistime)

                    intsphere_charge = photo
                    intsphere_electrons = intsphere_charge / (1.6*10**(-19))
                    totphoton = intsphere_electrons * throughput / QE_Thorlabs_PD
                    totphotons.append(totphoton)

                if doShutter:
                    cbp.shutter.main(runtype = "shutter", val = -1)
                else:
                    cbp.shutter.main(runtype = "shutter", val = 1)
                while elapsed_time < duration:
                    thistime = time.time()
                    elapsed_time = thistime - start_time

                    photo = ins1.getread()[0]
                    intsphere_charge = photo
                    intsphere_electrons = intsphere_charge / (1.6*10**(-19))
                    totphoton = intsphere_electrons * throughput / QE_Thorlabs_PD

                    photo1.append(photo)
                    times.append(thistime)
                    totphotons.append(totphoton)

                #time.sleep(duration)
                cbp.shutter.main(runtype = "shutter", val = 1)

                for ii in xrange(10):
                    thistime = time.time()
                    elapsed_time = thistime - start_time

                    photo = ins1.getread()[0]

                    photo1.append(photo)
                    times.append(thistime)

                    intsphere_charge = photo
                    intsphere_electrons = intsphere_charge / (1.6*10**(-19))
                    totphoton = intsphere_electrons * throughput / QE_Thorlabs_PD
                    totphotons.append(totphoton)

            elif (analysisType == 'photons') or (analysisType == 'charge'):

                times = []
                photo1 = []
                totphotons = []
                start_time = time.time()
                totphoton = 0
                intsphere_charge = 0

                fid = open(photonFile,'w') 
                for ii in xrange(10):
                    photo = ins1.getread()[0]
                    elapsed_time = time.time() - start_time
                    
                    photo1.append(photo)
                    times.append(elapsed_time)

                    intsphere_charge = photo1
                    intsphere_electrons = intsphere_charge / (1.6*10**(-19))
                    totphoton = intsphere_electrons * throughput / QE_Thorlabs_PD                  
                    totphotons.append(totphoton)
                    if analysisType == "photons":
                        print "%.0f/%.0f"%(totphoton,photons)
                    elif analysisType == "charge":
                        print "%.5e/%.5e"%(intsphere_charge,charge)
                    fid.write("%.10f %.10e %.0f\n"%(elapsed_time,photo1,totphoton))         

                cbp.shutter.main(runtype = "shutter", val = -1)
                if analysisType == "photons":
                    while totphoton < photons:
                        photo1 = ins1.getread()[0]
                        elapsed_time = time.time() - start_time

                        photos1.append(photo1)
                        times.append(elapsed_time)

                        intsphere_charge = photo1
                        intsphere_electrons = intsphere_charge / (1.6*10**(-19))
                        totphoton = intsphere_electrons * throughput / QE_Thorlabs_PD    
                        totphotons.append(totphoton)

                        print "%.0f/%.0f"%(totphoton,photons)
                        fid.write("%.10f %.10e %.0f\n"%(elapsed_time,photo1,totphoton))
                elif analysisType == "charge":
                    while intsphere_charge < charge:
                        photo1 = ins1.getread()[0]
                        elapsed_time = time.time() - start_time
                    
                        photos1.append(photo1)
                        times.append(elapsed_time)
                    
                        intsphere_charge = photo1
                        intsphere_electrons = intsphere_charge / (1.6*10**(-19))
                        totphoton = intsphere_electrons * throughput / QE_Thorlabs_PD               
                        totphotons.append(totphoton)

                        print "%.5e/%.5e"%(intsphere_charge,charge)
                        fid.write("%.10f %.10e %.0f\n"%(elapsed_time,photo1,totphoton))            
                cbp.shutter.main(runtype = "shutter", val = 1)

                for ii in xrange(10):
                    photo1 = ins1.getread()[0]
                    elapsed_time = time.time() - start_time

                    photos1.append(photo1)
                    times.append(elapsed_time)

                    intsphere_charge = photo1
                    intsphere_electrons = intsphere_charge / (1.6*10**(-19))
                    totphoton = intsphere_electrons * throughput / QE_Thorlabs_PD
                    totphotons.append(totphoton)

                    if analysisType == "photons":
                        print "%.0f/%.0f"%(totphoton,photons)
                    elif analysisType == "charge":
                        print "%.5e/%.5e"%(intsphere_charge,charge)

                    fid.write("%.10f %.10e %.0f\n"%(elapsed_time,photo1,totphoton))

                fid.close()
                photo1 = photos1    
        #except:
        #    times = [-1]
        #    photo1 = [-1]
        #    totphotons = [-1]
        #print times, photo1, totphotons
        return times, photo1, totphotons
    else:
        try:
            ins1 = Keithley(rm = rm, resnum = 0, mode = mode, doReset = doReset)
            #ins2 = Keithley(rm = rm, resnum = 1, mode = mode, doReset = doReset)
            time.sleep(duration)
            photo1 = ins1.getread()
            #photo2 = ins2.getread()
            photo2 = [-1,-1,-1]
        except:
            photo1 = [-1,-1,-1]
            photo2 = [-1,-1,-1]

        return photo1[0], photo2[0]


def main(runtype="keithley", duration=1, photons=100000, charge=10**-6, wavelength=550, mode='curr',
         analysisType="duration", doSingle=False, doReset=False, photonFile='test.dat', doShutter=True):

    if runtype == "keithley":
        rm = visa.ResourceManager('@py')
        if doSingle:
            times, photos, totphotons = get_keithley(rm = rm, duration = duration, mode = mode, photons = photons,
                                                     charge = charge, wavelength = wavelength,
                                                     analysisType = analysisType, doSingle = doSingle, doReset = doReset,
                                                     photonFile = photonFile, doShutter = doShutter)
            print times, photos, totphotons
            return times, photos, totphotons
        else:
            photo1, photo2 = get_keithley(rm = rm, duration = duration, mode = mode, photons = photons, charge = charge,
                                          wavelength = wavelength, analysisType = analysisType, doSingle = doSingle,
                                          doReset = doReset, photonFile = photonFile, doShutter = doShutter)
            print photo1, photo2 
            return photo1, photo2

if __name__ == "__main__":

    # Parse command line
    opts = parse_commandline()

    if opts.doKeithley:
        main(runtype="keithley",duration=opts.duration, photons=opts.photons, charge=opts.charge,
             wavelength=opts.wavelength, mode=opts.mode, analysisType=opts.analysisType, doSingle=opts.doSingle,
             doReset=opts.doReset, photonFile=opts.photonFile, doShutter=opts.doShutter)

