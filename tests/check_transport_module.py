"""Compile/run the actual Fortran transport with minimal Pencil data stubs.
No simulation jobs are launched. Requires gfortran and the Pencil source headers.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

STUBS = '''module Cdata
 implicit none
 integer,parameter::nx=24,ny=8,nz=8,nghost=3,ikind8=8
 integer,parameter::l1=4,l2=27,m1=4,m2=11,n1=4,n2=11
 integer::m=m1,n=n1,irho=1,iproc=0,it=0,it1=1
 real::t=0,cdt=.25,dx_1(30)=1,dy_1(14)=1,dz_1(14)=1,dt1_max(nx)=0
 logical::lroot=.true.,lupdate_courant_dt=.true.,ldt_paronly=.false.,lfirst=.true.
 logical::lactive_dimension(3)=[.true.,.true.,.true.]
end module
module Quiet
contains
 subroutine keep_compiler_quiet(i)
 integer,intent(in)::i
 end subroutine
end module
module Syscalls
 interface copy_addr
 module procedure copy_int,copy_real
 end interface
contains
 subroutine copy_int(x,y)
 integer,intent(in)::x
 integer(8),intent(out)::y
 y=0
 end subroutine
 subroutine copy_real(x,y)
 real,intent(in)::x
 integer(8),intent(out)::y
 y=0
 end subroutine
end module
module General
contains
 integer function string_to_enum(s)
 character(*),intent(in)::s
 string_to_enum=0
 end function
end module
'''
DRIVER = '''program check
 use Cdata
 use KT_transport
 implicit none
 real::f(30,14,14,4),de(nx),dm(nx,3),expected(nx),flux(30,14,14),p(30,14,14)
 real::phase,energy,px,py,pz,total(4),s2,zeroerr,maxerr
 integer::i,j,k,dir,comp,mode,u
 character(16)::modes(2)=['d6              ','adaptive        ']
 character(32)::test_case
 call get_command_argument(1,test_case)
 call kt_init(1,2,0,0.0,0.0,2.0)
 do k=1,14
 do j=1,14
 do i=1,30
 phase=2*acos(-1.0)*real(i-l1)/nx
 energy=1.0+.02*sin(phase)+.01*cos(2*acos(-1.0)*real(j-m1)/ny)
 px=.04*sin(phase); py=.03*cos(2*acos(-1.0)*real(j-m1)/ny)
 pz=.01*sin(2*acos(-1.0)*real(k-n1)/nz)
 f(i,j,k,:)=[energy,px,py,pz]
 s2=px**2+py**2+pz**2
 p(i,j,k)=energy*(2*sqrt(1-.75*s2/energy**2)-1)/3
 enddo
 enddo
 enddo
 ! D6 flux identity, all components, all active directions; in this smooth
 ! field thresholds .03/.03 yield no flags, so adaptive must also equal D6.
 maxerr=0; total=0
 do n=n1,n2
 do m=m1,m2
 call kt_div(f,de); call kt_div_tensor(f,dm)
 do comp=1,4
 expected=0
 do dir=1,3
 if(comp==1) then
 flux=f(:,:,:,1+dir)
 else
 flux=f(:,:,:,1+dir)*f(:,:,:,comp)/(f(:,:,:,1)+p)
 if(comp==dir+1) flux=flux+p
 endif
 do i=1,nx
 select case(dir)
 case(1)
 expected(i)=expected(i)+.75*(flux(l1+i,m,n)-flux(l1+i-2,m,n)) &
 -.15*(flux(l1+i+1,m,n)-flux(l1+i-3,m,n)) &
 +(flux(l1+i+2,m,n)-flux(l1+i-4,m,n))/60
 case(2)
 expected(i)=expected(i)+.75*(flux(l1+i-1,m+1,n)-flux(l1+i-1,m-1,n)) &
 -.15*(flux(l1+i-1,m+2,n)-flux(l1+i-1,m-2,n)) &
 +(flux(l1+i-1,m+3,n)-flux(l1+i-1,m-3,n))/60
 case(3)
 expected(i)=expected(i)+.75*(flux(l1+i-1,m,n+1)-flux(l1+i-1,m,n-1)) &
 -.15*(flux(l1+i-1,m,n+2)-flux(l1+i-1,m,n-2)) &
 +(flux(l1+i-1,m,n+3)-flux(l1+i-1,m,n-3))/60
 endselect
 enddo
 enddo
 if(comp==1) then
 maxerr=max(maxerr,maxval(abs(de-expected)))
 total(comp)=total(comp)+sum(de)
 else
 maxerr=max(maxerr,maxval(abs(dm(:,comp-1)-expected)))
 total(comp)=total(comp)+sum(dm(:,comp-1))
 endif
 enddo
 enddo
 enddo
 print *, 'SMOOTH D6 IDENTITY ERROR',maxerr
 print *, 'PERIODIC CONSERVATION',maxval(abs(total))
 if(test_case/='sensitive'.and.maxerr>1e-12) error stop 'D6 identity failed'
 if(maxval(abs(total))>1e-10) error stop 'Smooth conservation failed'
 ! A periodic compressive, discontinuous state: adaptive faces switch in a
 ! subset of the domain. Shared flux differences must still telescope in 3D.
 do k=1,14
 do j=1,14
 do i=1,30
 if(modulo(i-l1,nx)<nx/2) then
 f(i,j,k,:)=[1.0,.12,.01,0.0]
 else
 f(i,j,k,:)=[.5,-.12,.01,0.0]
 endif
 enddo
 enddo
 enddo
 total=0
 do n=n1,n2
 do m=m1,m2
 call kt_div(f,de); call kt_div_tensor(f,dm)
 total(1)=total(1)+sum(de)
 total(2:4)=total(2:4)+sum(dm,dim=1)
 enddo
 enddo
 print *, 'MIXED FACE CONSERVATION',maxval(abs(total))
 if(maxval(abs(total))>1e-10) error stop 'Adaptive conservation failed'
end program
'''

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--pencil',type=Path,default=Path.home()/'Work/research/software/pencil-code')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='kaai-transport-') as tmp:
        build=Path(tmp)
        (build/'data').mkdir()
        (build/'stubs.f90').write_text(STUBS)
        (build/'driver.f90').write_text(DRIVER)
        shutil.copy(args.pencil/'src/kt_transport.h',build)
        subprocess.run(['gfortran','-O0','-g','-fcheck=all','-ffpe-trap=invalid,zero,overflow',
                        '-fdefault-real-8','-fdefault-double-8', '-ffree-line-length-none', '-I.',
                        'stubs.f90',str(root/'numerics/kt_transport_experiment.f90'),
                        'driver.f90','-o','check'],cwd=build,check=True)
        # Driver tests both routes in separate processes via module initialization.
        for mode,threshold,sensitive in [('d6',.0001,False),('adaptive',.03,False),('adaptive',.0001,True)]:
            (build/'transport.in').write_text('&transport_experiment transport_mode="'+mode+'" '
                +'compression_threshold='+str(threshold)+' pressure_threshold='+str(threshold)+' /\n')
            subprocess.run([str(build/'check'),'sensitive' if sensitive else 'identity'],cwd=build,check=True)
            records=[line.split() for line in (build/'data/transport-rank000000.dat').read_text().splitlines()]
            smooth, mixed=records[-2:]
            if sensitive:
                assert int(smooth[2])>0, 'Small thresholds should flag this smooth compression: document false positives'
            else:
                assert int(smooth[2])==0, 'Smooth identity test unexpectedly flagged'
            if mode=='adaptive':
                assert 0<int(mixed[2])<int(mixed[3]), 'Mixed test must select both methods'
            else:
                assert int(mixed[2])==0, 'D6 control selected KT'
        # The smooth-case initial D6 equality above does not apply to KT mode.
        print('Actual Fortran module: D6 identity and mixed-face conservation checks passed.')
if __name__=='__main__': main()
