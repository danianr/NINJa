#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#include <arpa/inet.h>
#include <string.h>
#include <search.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/types.h>
#include <signal.h>
#include <netdb.h>
#include <unistd.h>
#include <pthread.h>


#define DEFAULT_CONTROL_PATH "/tmp/keepersock"
#define DEFAULT_MCAST_ADDRESS "233.0.14.56"
#define DEFAULT_MCAST_PORT "34426"

#ifndef SO_REUSEPORT
#define SO_REUSEPORT 15
#endif

struct jobinfo {
    char uuid[32];
    char sha512[128];
    unsigned long created;
    unsigned int pageinfo;
    struct in_addr src;
    struct in_addr dst;
    char username[16];
    char title[64];
    struct jobinfo *next;
};


struct userqueue {
    char username[16];
    unsigned long cleaned;
    struct jobinfo *head;
};


struct circular_queue {
    struct userqueue *queue;
    unsigned long *cleaned;
    struct circular_queue  *prev;
    struct circular_queue  *next;
};


#define NUM_USERS 30000
#define EXPIRE_TIME 14400


unsigned long clean_queue(struct userqueue *q, unsigned long duration){
    struct jobinfo *j, *p;
    unsigned long now;

    now = time(NULL);
    j = q->head;
    while ( (j != NULL) && (j->created + duration < now)){
       q->head = j->next;
       p = j;
       j = j->next;
       free(p);
    }

    return now;
}


void reaper(struct circular_queue *q){
   unsigned int sleeptime = 6;
   unsigned int sleepevery = 100;
   unsigned int counter = 1;
   int shutdown = 0;
 
   unsigned long examine;

   while (!shutdown){
      examine = time(NULL) - sleeptime;
      if ( *q->cleaned < examine ) clean_queue(q->queue, EXPIRE_TIME);
      q = q->next;
      if ( (counter++ % sleepevery) == 1) {
         counter = 0;
         sleep(sleeptime);
      }
   }
   return;
}


struct jobinfo *find_job(struct userqueue *q, char *uuid,
                         unsigned long created, struct in_addr *dst){
     struct jobinfo *j;

     j = q->head;
     while (j != NULL){
        if ( j->created == created  &&
             (memcmp(&j->dst, dst, sizeof(struct in_addr)) == 0 )  &&
             (strncmp(j->uuid, uuid, 32) == 0) ) return j;
        j = j->next;
     }
     return j;
}


void append_job(struct userqueue *q, char *username, char *sha512, char *uuid,
                char *title, unsigned long created, int pages, int duplex,
                struct in_addr *src, struct in_addr *dst){

     struct jobinfo *j, *p;
     q->cleaned = clean_queue(q, EXPIRE_TIME);

     /* don't allocate memory or add job if it exists already
        even though jobs are uniquely identified by uuid and
        the cups server to which it was submitted, creation
        time is a much eaiser first pass comparison */
     if ( find_job(q, uuid, created, dst) ) return;

     j = (struct jobinfo *) malloc(sizeof(struct jobinfo));
     memset(j, 0, sizeof(struct jobinfo));

     memcpy(j->uuid, uuid, 32);
     memcpy(j->sha512, sha512, 128);
     j->created = created;
     j->pageinfo = (pages << 1) + duplex;
     memcpy(&j->src, src, sizeof(struct in_addr));
     memcpy(&j->dst, dst, sizeof(struct in_addr));

     strncpy(j->username, username, 15);
     strncpy(j->title, title, 63);

     if (q->head == NULL){
         q->head = j;
     }else{
         p = q->head;

         /* Progress through the joblist until the next
            slot is either NULL or occupied by a job of
            equal or greater creation time */

         while (p->next && (p->next->created < created) ){
            p = p->next;
         }

         /* If the next slot is non-NULL, then move that
            slot's jobinfo into the next address of this
            new jobinfo structure and change the p->next
            to point to our new structure, inserting it
            before the occupied slot */

         if ( p->next ){
            j->next = p->next;
         }
         p->next = j;
     }
        
}



#define INDEX_REQUEST 1
#define BULK_LOAD     2
#define EXPORT        3
#define INVALIDATE    5
#define SHUTDOWN      6
#define UNKNOWN      -1

int control_command(char *cmdbuffer, char **arg_offset){
   if (strncmp(cmdbuffer, "return", 6) == 0){
      *arg_offset = &cmdbuffer[7];
      return INDEX_REQUEST;
   }else if (strncmp(cmdbuffer, "delete", 6) == 0){
      *arg_offset = &cmdbuffer[7];
      return INVALIDATE;
   }else if (strncmp(cmdbuffer, "export", 6) == 0){
      *arg_offset = &cmdbuffer[7];
      return EXPORT;
   }else if (strncmp(cmdbuffer, "shutdown", 8) == 0){
      *arg_offset = NULL;
      return SHUTDOWN;
   }

   *arg_offset = cmdbuffer;
   return UNKNOWN;
}



/* control socket descriptor in the global scope
   so as to be availble from signal handlers     */
int csd;
void clean_exit(){
    struct sockaddr_un *sockaddr;
    socklen_t size = 1024;

    sockaddr = (struct sockaddr_un *)  malloc(1024);
    if ( getsockname(csd, (struct sockaddr *) sockaddr, &size) == 0){
       close(csd);
       unlink(sockaddr->sun_path);
    }else{
       close(csd);
    }
    free(sockaddr);
    exit(0);
}
       
    
void control_channel(char **socketpath){
   /* int csd is in the global scope, see above
      and contains the file descriptor of the control socket */

   struct sockaddr_un un, cliun;
   struct jobinfo *j;
   int size,br, len, clifd, shutdown=0;
   char *cmdbuf, *username, *argument, *sp;         /* cmd parsing */
   char *uuid, *sha512, *client, *printer, *title;  /* display buffers */
   ENTRY item, *found_item;                         /* hashmap structs */


   /* tie the hashmap query directly to the username buffer */
   username = (char *) malloc(16);
   memset(username, 0, 16);
   item.key = username;


   /* linux does not require the length of the sockaddr_un to be specified */
   len = sizeof(cliun);
   cmdbuf = (char *) malloc(1024);
   un.sun_family = AF_UNIX;
   strcpy(un.sun_path, socketpath[0]);
   csd = socket(AF_UNIX, SOCK_STREAM, 0);
   size = offsetof(struct sockaddr_un, sun_path) + strlen(un.sun_path);

   if (bind(csd,  (struct sockaddr *) &un, size) < 0){
       perror("bind failed");
       close(csd);
       exit(1);
   }else{
       signal(SIGINT,  clean_exit);
       signal(SIGTERM, clean_exit);
   }

   /* we should never be processing more than 1 command anyway */ 
   listen(csd, SOMAXCONN);
   while(!shutdown){

      /* make the accept a little more tollerent */
      if (( clifd = accept(csd, (struct sockaddr *) &cliun, &len)) < 0) continue;


      /* argument will hold the pointer to the start of the argument (if any)
         after processing by the control_command function, so pass it by ref */
      memset(cmdbuf, 0, 1024);
      br = read(clifd, cmdbuf, 1024);
      switch (control_command(cmdbuf, &argument)){

         case INDEX_REQUEST:

            memset(username, 0, 16);
            /* remove any trailing spaces */
            if (sp=memccpy(username, argument, 32, 16)) *sp = '\0';

            if (found_item = hsearch(item, FIND)){
                j = ((struct userqueue *) found_item->data)->head;
                client  = (char *) malloc(256);
                printer = (char *) malloc(256);
                uuid    = (char *) malloc(33);
                sha512  = (char *) malloc(129);
                title   = (char *) malloc(65);
                memset(uuid,   0, 33);
                memset(sha512, 0,129);
                memset(title,  0, 65);

                while (j){
                  char *serv;
                  memset(client,  0, 256);
                  memset(printer, 0, 256);
                  inet_ntop(AF_INET, &j->src, client, 256);
                  inet_ntop(AF_INET, &j->dst, printer, 256);
                  strncpy(uuid,   j->uuid,    32);
                  strncpy(sha512, j->sha512, 128);
                  strncpy(title,  j->title,   64);

                  /* While the colon is visually nice, it appears too often in the title,
                     thus the use of the ASCII Field Separator (fs) character, a non-printing
                     character of decimal value 28 (034); newlines are not allowed so they
                     still represent a logical record separator as opposed to the ASCII (036) */
                  dprintf(clifd, "%32s\034%128s\034%lu\034%u\034%s\034%s\034%s\034%s\n", 
                          uuid, sha512, j->created, j->pageinfo, client, printer, username, title);
                  j=j->next;
                }

                /* clean up strings */
                if (client)  free(client);
                if (printer) free(printer);

            }else{
                printf("No jobs found\n");
            }
            break;
            ;;

         case SHUTDOWN:
            shutdown=1;
            dprintf(clifd, "Acknowledged shutdown command.\n");
            break;
            ;;

         case UNKNOWN:
         default:
            dprintf(clifd, "unknown command: %s\n", argument);
            break;
            ;;
      }   
      close(clifd);
   }
   clean_exit();
   return;
}



struct ip_mreq     group;
int                sd;


#define BUFSIZE 294

/* Records widths and offsets */
#define UUIDSIZE 32

#define SHA512SIZE 128
#define SHA512OFFSET   ( UUIDSIZE )

#define CREATIONSIZE 20
#define CREATIONOFFSET ( SHA512OFFSET + SHA512SIZE )

#define PAGESSIZE  5
#define PAGESOFFSET  ( CREATIONOFFSET + CREATIONSIZE )

#define DUPLEXSIZE 1
#define DUPLEXOFFSET ( PAGESOFFSET + PAGESSIZE )

#define SRCSIZE 16
#define SRCOFFSET ( DUPLEXOFFSET + DUPLEXSIZE )

#define DSTSIZE 16
#define DSTOFFSET ( SRCOFFSET + SRCSIZE - 1 )

#define USERSIZE 16
#define USEROFFSET ( DSTOFFSET + DSTSIZE - 1 )

#define TITLESIZE 64
#define TITLEOFFSET ( USEROFFSET + USERSIZE - 1)


int main(int argc, char **argv){
   ENTRY item;
   ENTRY *found_item;
   struct circular_queue *circular=NULL, *c;
   struct userqueue *queue;
   struct jobinfo *j;
   char *src, *dst, *mcastaddr, *port;
   struct in_addr *isrc, *idst;
   char uuid[UUIDSIZE], sha512[SHA512SIZE], username[USERSIZE], title[TITLESIZE];
   unsigned long created;
   unsigned int pages, duplex;
   char buf[BUFSIZE];
   char *pages_str, *created_str;
   char *hostname, *interface, *p;
   char *controlpath[2] = { DEFAULT_CONTROL_PATH, "" };
   struct addrinfo *hints, **res;
   int ecode, optval, ctrl, bytes_read = 0;
   pthread_t control_tid, reaper_tid;


   mcastaddr = DEFAULT_MCAST_ADDRESS;
   port = DEFAULT_MCAST_PORT;
   switch (argc){

       case 1:
            dprintf(1, "Using default values\n");
            break;;

       case 2:
            if ( strncmp("-t", argv[1], 2) == 0 ){
                port = DEFAULT_MCAST_PORT - 1;
            }else{
                port = strdup(argv[1]);
            }
            break;;

       case 3:
            mcastaddr = strdup(argv[1]);
            port = strdup(argv[2]);
            break;;

       case 4:
            mcastaddr = strdup(argv[1]);
            port = strdup(argv[2]);
            controlpath[0] = strdup(argv[3]);
            break;;

       default:
            dprintf(2, "Incorrect number number of arguments\n");
            exit(-1);
            break;;
   }
   dprintf(1, "Using multicast group %s:%s\n", mcastaddr, port);
   dprintf(1, "Using UNIX socket %s for control\n", controlpath[0]);


   hcreate(NUM_USERS);


   pthread_create(&control_tid, NULL, (void *) &control_channel, controlpath);

   hints = (struct addrinfo *) malloc(sizeof(struct addrinfo));
   memset(hints, 0, sizeof(struct addrinfo));
   hints->ai_family = AF_INET;
   hints->ai_socktype = SOCK_DGRAM;
   hints->ai_protocol = IPPROTO_UDP;
   hints->ai_flags    = AI_PASSIVE;


  
   optval = 1; 
   sd = socket(AF_INET, SOCK_DGRAM, 0);
   setsockopt(sd, SOL_SOCKET, SO_REUSEADDR, &optval, sizeof(optval));
   setsockopt(sd, SOL_SOCKET, SO_REUSEPORT, &optval, sizeof(optval));
   setsockopt(sd, IPPROTO_IP, IP_MULTICAST_LOOP, &optval, sizeof(optval));

   optval = 3;
   setsockopt(sd, IPPROTO_IP, IP_MULTICAST_TTL, &optval, sizeof(optval));


   res = (struct addrinfo **) malloc(sizeof(struct addrinfo **));   
   getaddrinfo(NULL, port, hints, res);
   if (bind(sd, res[0]->ai_addr, res[0]->ai_addrlen) ) {
      perror("error binding datagram socket");
      close(sd);
      exit(1);
   }else{
      freeaddrinfo(res[0]);
   }

   hints->ai_flags = 0;
   hostname  = (char *) malloc(256);
   memset(hostname, 0, 256);
   gethostname(hostname, 256);
   getaddrinfo(hostname, port, hints, res);


   /* the ip_mreq is still using a legacy in_addr, so convert from the ai_addr */
   interface = (char *) malloc(16);
   memset(interface, 0, 16);
   ecode = getnameinfo(res[0]->ai_addr, res[0]->ai_addrlen, interface, 16, NULL, 0, NI_NUMERICHOST);

   if (ecode){
      perror(gai_strerror(ecode));
      close(sd);
      exit(1);
   }
      
   inet_pton(AF_INET, interface, &group.imr_interface.s_addr);
   inet_pton(AF_INET, mcastaddr, &group.imr_multiaddr.s_addr);

   if (setsockopt(sd, IPPROTO_IP, IP_ADD_MEMBERSHIP, (char *)&group, sizeof(group)) < 0){
     perror("error adding multicast group");
     close(sd);
     exit(1);
   }
   


   while(1){
     memset(buf,0, BUFSIZE);
     bytes_read = recv(sd, buf, BUFSIZE, 0);
     printf("RECIEVED: %4d bytes [%s]\n", bytes_read, buf);
     if (read < 0 ) {
        perror("error reading datagram message");
        close(sd);
        exit(1);
     }

     memcpy(uuid, buf, UUIDSIZE);
     memcpy(sha512, &buf[SHA512OFFSET], SHA512SIZE);

     pages_str = strndup(&buf[PAGESOFFSET], PAGESSIZE);
     pages = strtol( pages_str, NULL, 10);

     created_str = strndup(&buf[CREATIONOFFSET], CREATIONSIZE);
     created = strtol(created_str, NULL, 10);

     duplex = (buf[DUPLEXOFFSET] = '1')? 1 : 0;
     free(created_str);    
     free(pages_str);

     memset(username, 0, USERSIZE);
     if (p = memccpy(username, &buf[USEROFFSET], 32, USERSIZE - 1)){
         *--p='\0';
     }
     memset(title, 0, TITLESIZE);
     memcpy(title, &buf[TITLEOFFSET], TITLESIZE - 1 );
 

     /* IP address is a zero-padded dotted quad, using
        inet_aton() will result in zero-padded octets
        being treated as octal, inet_pton() does not
        exhibit this behavior [and also will not accept
        hex-digits either], so inet_aton() and inet_pton()
        should not be intermixed. */

     src = (char *) malloc(SRCSIZE);
     memset(src, 0, SRCSIZE);
     memcpy(src, &buf[SRCOFFSET], SRCSIZE - 1);

     dst = (char *) malloc(DSTSIZE);
     memset(dst, 0, DSTSIZE - 1);
     memcpy(dst, &buf[DSTOFFSET], DSTSIZE - 1);

     isrc = (struct in_addr *) malloc( sizeof(struct in_addr));
     idst = (struct in_addr *) malloc( sizeof(struct in_addr));
     memset(isrc, 0, sizeof(struct in_addr));
     memset(idst, 0, sizeof(struct in_addr));
     if ( inet_pton(AF_INET, src, isrc) == 0){
        inet_pton(AF_INET, "0.0.0.0", isrc);
     }

     if ( inet_pton(AF_INET, dst, idst) == 0){
        inet_pton(AF_INET, "0.0.0.0", idst);
     }

     item.key = strdup(username);

     if (found_item = hsearch(item, FIND)){
        append_job( (struct userqueue *) found_item->data, username, sha512, uuid, title, created,
                pages, duplex, isrc, idst );
     }else{
        queue = (struct userqueue *) malloc(sizeof(struct userqueue));
        memset(queue, 0, sizeof(struct userqueue));
        strncpy(queue->username, username, USERSIZE - 1);
        append_job( queue, username, sha512, uuid, title, created,
                pages, duplex, isrc, idst );
        item.data = queue;
        if (!circular){
           /* create the circular queue with a single element, doubly-linked to itself */
           circular = (struct circular_queue *) malloc(sizeof(struct circular_queue));
           circular->queue = queue;
           circular->next = circular;
           circular->prev = circular;
           circular->cleaned = &queue->cleaned;
           pthread_create(&reaper_tid, NULL, (void *) &reaper, circular);
        }else{
           /* Prepend the new queue to the circular queue, ensuring a full cycle
              before it is reached */
           c = (struct circular_queue *) malloc(sizeof(struct circular_queue));
           c->queue = queue;
           c->cleaned = &queue->cleaned;
           c->next = circular;
           c->prev = circular->prev;
           circular->prev->next = c;
           circular->prev = c;
        }
        hsearch(item, ENTER);
     }
     free(isrc);
     free(idst);
     free(src);
     free(dst);
   }

   return 0;
}
