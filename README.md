NINJa
=====

NINJa is a print release and accounting front-end application for use with
the PageServer authorization and accounting backend Servlet.


History
=======
This project grew out of an initiative to replace Columbia University's
second print management in-house solution, NINJa, which itself replaced
Jake, Columbia's original print-release platform.

   Jake
   ----
   The Jake print release system, written by Columbia around 1991, used
   X-terminals connected to Sun Microsystems servers to release jobs
   from a central print queue.  While effective, this system experienced
   several domain-wide outages.  A common complaint was that a hanging
   client submitting a job or a crashed Xserver could disable printing
   for the entire University.


   NINJa (pcd backend)
   --------------------
   Begining in 2002, the Jake print release system was replaced by
   NINJa (NINJa Is Not Jake).  The NINJa system heavily leveraged early
   Java frameworks such as Apache River, Java WebStart, and RMI.  The
   design utilized the Teahouse GUI framework to render HTML markup into
   a table-based clien.  Each terminal ran a small custom linux
   distribution which PXE-booted and pulled the most current version of
   the client-release software via WebStart.  Initially users and their
   associated population information were stored within the same database
   used to track printing usage, however after performance problems with
   the shared database necessitated splitting out the print accounting
   tables, account information was provided via LDAP.  Additional information
   can be found on this generation of Columbia's print release system from
   this 2004 EDUCause presentation: [ninja_educause](docs/ninja_educause2005.pdf)
