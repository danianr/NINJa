History
=======
This project grew out of an initiative to replace Columbia University's
second print management in-house solution, NINJa, which itself replaced
Jake, Columbia's original print-release platform.

   Jake
   -----
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
   tables, account information was provided via LDAP.  A system of Perl and
   JavaServerPages provided a self-service gateway for users affiliated with
   the university (and already possessing an active Kerberos principal) to
   purchase additional printing credits online with a credit card.
   Additional information can be found on this generation of Columbia's
   print release system from this 2004 EDUCause presentation: [ninja_educause2004.pdf](ninja_educause2004.pdf)


   NINJa (PageServer backend)
   ---------------------------
   Starting with the replacement of the JavaServerPages self-service
   interface in 2008, the backend processing of the NINJa system was
   reworked into a stand-alone JavaServlet providing all non-client
   functionality of the print authorization and accounting service.
   While the primary aim of this refactoring was to consolidate database
   access to a single, unified interface point, recurring LDAP performance
   issues required the stability of a caching layer and persistent
   bound connections.  Compiled XSLT templates provided a way to separate
   the presentation layer from the business logic, while the integration
   of support tools removed the last of the stand-alone scripts required
   for the credit of marred (streaked due to low toner) printing jobs.

