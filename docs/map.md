Project Map
===========


[ninja.py](../ninja.py) Entry point for __main__, platform specific configuration options go
           here as well as any pre-execution configuration such as the setup of
           print queues, discovery/definition of grid nodes, and the name of the
           associated private queue.


[controller.py](../controller.py)  Controller: Top logical-level object of the NINJa service.
                 Use the start() / stop() methods to manage the service.  All
                 objects whose interfaces are accessed by multiple classes should
                 be instantiated within this object's intializer.

[jobqueue.py](../jobqueue.py)    Application-level representation of incomplete CUPS jobs and their
                 mappings to both identified and unmapped submitting users.  This file
                 contains three classes: Job, JobMapping, and JobQueue.

                 Job: Application representation of a print job submitted to the local
                      CUPS public queue.  Additional values of the document's SHA512
                      digest and computed pagecount are used by the distributed storage
                      grid.

                 JobQueue: Object to keep track of previously processed submitted jobs,
                           to provide a quick lookup of all submitted jobs for a given
                           user (whose username matches the regular expression supplied
                           in unipattern), and to advertise all jobs whose username
                           matches unipattern to the storage grid.

                 JobMapping: Point-in-time read-only mapping between a Job and its
                             textual representation, used in building the Tkinter::Listbox
                             display.  The interator provides the string representation
                             suitable for display in the Listbox, while the element accessor
                             __get_item__ and .map() method provide the associated Job
                             for a given position within the list.


[multicast.py](../multicast.py)  MulticastMember: interface class to publish the header
                 information of a Job object supplied to the advertise method to all
                 nodes participating within the multicast storage grid system.

[cloudadapter.py](../cloudadapter.py)  CloudAdapter: Adapter class which communicates between
                 the running python environment and the multicast cache deamon, which runs as
                 a separate process.  Additionally, this class provides the interface methods
                 to store a document to, and retreive a document from the storage grid given
                 a username and the SHA512 digest of its content.

[authdialog.py](../authdialog.py)  AuthDialog:  Subclassed Tkinter::Toplevel multi-field text
                 Entry box to supply a valid username and password; also contains the authentication
                 logic to process the supplied password via Kerberos

[pageserver.py](../pageserver.py)  PageServerAuth: class to perform authorization and accounting
                 via the PageServer Servlet backend.  authorizeJobs checks for available quota or
                 page credits and then calls releaseJob with the same requestId supplied in the
                 XML response from the server.  errorcb is used to display an error message to the
                 user.  Additionally, this class passes back any quota or system bulletin information
                 to the MessageDisplay class.

[messagedisplay.py](../messagedisplay.py)  MessageDisplay: class to parse a XML ElementTree for server
                 bulletins or quota information and update a registered Tkinter:Frame for display
                 of that information.

[mainscreen.py](../mainscreen.py) This represents the main, user-facing component of the program,
                 and is separated into four distinct classes, one of which is complex enough to
                 warrant its own file:

                 MainScreen: Frame to represent the entire display (Popup Toplevel elements are
                             handled separately), this acts as a sub-controller of the LocalFrame,
                             UnclaimedFrame, and RemoteFrame windows, handles most of the event
                             bindings, defines the errorCallback, and wraps the LocalFrame, RemoteFrame,
                             UnclaimedFrame, and the Frame used by MessageDisplay within a
                             tabbed ttk::Notebook.

                 LocalFrame: Tkinter::Listbox (with header Label) that encapsulates Job display and
                             selection tasks with associated authorization handling for print jobs
                             submitted to the local CUPS queue and claimed by the currently logged-in user.
                 
                 UnclaimedFrame: Tkinter::ListBox (with header Label) that encapsulates the Job display,
                                 selection, and authorization tasks for any jobs submitted to the local
                                 CUPS print queue that do not have a job-orgininating-user-name or have
                                 one which does not match the unipattern RE.

[remotescreen.py](../remotescreen.py) [See above]
                 RemoteFrame: Tkinter::Listbox (with header Label) that uses the CloudAdapter class to
                              query the multicast backend cache deamon for the logged-in user's print
                              jobs which reside throughout the job storage grid.  Also contains the
                              authorization logic (calling PageServerAuth) to authorize the request
                              prior to document retrieval and release.

[pagecount.sh](../pagecount.sh)  Bash (not bourne) shell script to provide an accurate count of the sheets
                   of paper a submitted document will require to print.  Requires that ghostscript is installed.

[multicast.c](../multicast.c)  Backend caching daemon which listens for job header information on
                   the multicast address shared by MulticastMember.  Provides a UNIX-domain socket
                   for access by the CloudAdapter as well as supplimentary control scripts.



-------------
Unit Testing

[mockjob.py](../mockjob.py) Mock object creating a sub-classed Job object for unit testing

[multicastinjector.py](../multicastinjector.py)  script to inject valid mock job objects

[multicasttests.py](../multicastests.py)  Test suite for the multicast job header advertisment
