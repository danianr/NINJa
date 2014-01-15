#!/usr/bin/perl


my $OPENSSL = q(/usr/bin/openssl);
my $SFTP    = q(/usr/bin/sftp);
my $remote_path = q(/spare/remote/%s/%s);

my @nodes = qw( avery200a-ninja.atg.columbia.edu.
		avery200b-ninja.atg.columbia.edu.
		bclibrary100a-ninja.barnard.columbia.edu.
		bclibrary200a-ninja.barnard.columbia.edu.
		broadway304a-ninja.atg.columbia.edu.
		brooks100a-ninja.barnard.columbia.edu.
		brooks100b-ninja.barnard.columbia.edu.
		burke100a-ninja.atg.columbia.edu.
		burke300a-ninja.atg.columbia.edu.
		butler209a-ninja.atg.columbia.edu.
		butler209b-ninja.atg.columbia.edu.
		butler213a-ninja.atg.columbia.edu.
		butler213b-ninja.atg.columbia.edu.
		butler213c-ninja.atg.columbia.edu.
		butler300a-ninja.atg.columbia.edu.
		butler300b-ninja.atg.columbia.edu.
		butler305a-ninja.atg.columbia.edu.
		butler401a-ninja.atg.columbia.edu.
		butler403a-ninja.atg.columbia.edu.
		butler501a-ninja.atg.columbia.edu.
		butler606a-ninja.atg.columbia.edu.
		campbell505a-ninja.atg.columbia.edu.
		carlton100a-ninja.atg.columbia.edu.
		carlton100b-ninja.atg.columbia.edu.
		carman103a-ninja.atg.columbia.edu.
		carman103b-ninja.atg.columbia.edu.
		claremntb01a-ninja.atg.columbia.edu.
		dcc413a-ninja.barnard.columbia.edu.
		dcc413b-ninja.barnard.columbia.edu.
		diana307a-ninja.barnard.columbia.edu.
		diana307b-ninja.barnard.columbia.edu.
		diana307c-ninja.barnard.columbia.edu.
		diana307d-ninja.barnard.columbia.edu.
		dodgeart412a-ninja.atg.columbia.edu.
		dodgeart701a-ninja.atg.columbia.edu.
		dodgeart701b-ninja.atg.columbia.edu.
		ec01a-ninja.atg.columbia.edu.
		ec10a-ninja.atg.columbia.edu.
		ec18a-ninja.atg.columbia.edu.
		et251a-ninja.atg.columbia.edu.
		et251b-ninja.atg.columbia.edu.
		et251c-ninja.atg.columbia.edu.
		et251color-ninja.atg.columbia.edu.
		furnald107a-ninja.atg.columbia.edu.
		harmony100a-ninja.atg.columbia.edu.
		hartley111a-ninja.atg.columbia.edu.
		hartley111b-ninja.atg.columbia.edu.
		iab215a-ninja.atg.columbia.edu.
		iab310a-ninja.atg.columbia.edu.
		iab323a-ninja.atg.columbia.edu.
		iab323b-ninja.atg.columbia.edu.
		iab323color-ninja.atg.columbia.edu.
		iab509a-ninja.atg.columbia.edu.
		kent300a-ninja.atg.columbia.edu.
		kent300b-ninja.atg.columbia.edu.
		lehman018a-ninja.barnard.columbia.edu.
		lerner200a-ninja.atg.columbia.edu.
		lerner200b-ninja.atg.columbia.edu.
		lerner300a-ninja.atg.columbia.edu.
		lerner300b-ninja.atg.columbia.edu.
		lewisohn300a-ninja.atg.columbia.edu.
		lewisohn300b-ninja.atg.columbia.edu.
		math303a-ninja.atg.columbia.edu.
		mcbain100a-ninja.atg.columbia.edu.
		mudd422a-ninja.atg.columbia.edu.
		mudd422b-ninja.atg.columbia.edu.
		nwcb400a-ninja.atg.columbia.edu.
		nwcb400b-ninja.atg.columbia.edu.
		nwcb600a-ninja.atg.columbia.edu.
		nwcb600b-ninja.atg.columbia.edu.
		plimpton100a-ninja.barnard.columbia.edu.
		plimpton100b-ninja.barnard.columbia.edu.
		riverb01a-ninja.atg.columbia.edu.
		ruggles100a-ninja.atg.columbia.edu.
		russell100a-ninja.tc.columbia.edu.
		schapiro108a-ninja.atg.columbia.edu.
		schermerhorn558a-ninja.atg.columbia.edu.
		schermerhorn601a-ninja.atg.columbia.edu.
		sicb01a-ninja.atg.columbia.edu.
		six00w113a-ninja.atg.columbia.edu.
		sixsixteen100a-ninja.barnard.columbia.edu.
		sixsixteen100b-ninja.barnard.columbia.edu.
		socialwork105a-ninja.atg.columbia.edu.
		socialwork105b-ninja.atg.columbia.edu.
		socialwork105c-ninja.atg.columbia.edu.
		socialwork105d-ninja.atg.columbia.edu.
		socialwork105e-ninja.atg.columbia.edu.
		socialwork202a-ninja.atg.columbia.edu.
		socialwork207a-ninja.atg.columbia.edu.
		socialwork214a-ninja.atg.columbia.edu.
		socialwork309a-ninja.atg.columbia.edu.
		socialwork401a-ninja.atg.columbia.edu.
		socialwork721a-ninja.atg.columbia.edu.
		socialwork821a-ninja.atg.columbia.edu.
		socialwork900a-ninja.atg.columbia.edu.
		stat902a-ninja.atg.columbia.edu.
		sulzberger100a-ninja.barnard.columbia.edu.
		uris130a-ninja.atg.columbia.edu.
		uris130b-ninja.atg.columbia.edu.
		uris130c-ninja.atg.columbia.edu.
		uris130d-ninja.atg.columbia.edu.
		watt100a-ninja.atg.columbia.edu.
		wien211a-ninja.atg.columbia.edu.
		wien211b-ninja.atg.columbia.edu.
		woodbridge100a-ninja.atg.columbia.edu. );

# mark all nodes alive
my %alive;
map { $alive{$_} = 1; } @nodes;

sub crypts($$){
    my $crypt_name = $_[0];
    my $num_replication = $_[1];
    my @selected;
    my $seed = 42;
    my $j = 1;
    map { $seed *= ord($_) / $j++; } split //, $crypt_name;
    srand(int($seed));
    while ($num_replication--){
      my $i = int(rand(@nodes)) % @nodes;
      push @selected, $nodes[$i];
    }
    return @selected;
}



sub put($$$){
   my $queue    = $_[0];
   my $filename = $_[1];
   my $replication = $_[2];

   my $sha512 = qx($OPENSSL dgst -sha512 $filename);
   if ($? != 0 ){
      die "Unable to obtain a sha512 checksum, aborting: $!";
   }else{
      $sha512 =~ s/^.*= //;
   }

   SELECTION:
      @selected = grep { $alive{$_} } crypts($queue, $replication);
      while  ( @selected < $replication ){
         my $extra = ( $replication - @selected );
         @selected = grep { $alive{$_} } crypts($queue, $replication + $extra);
      }

   foreach $remote_host (@selected){
      open my $remote_sftp, "| $SFTP -b- ${remote_host}";

      print $remote_sftp <<__END_SFTP_CMDS__;
cd ${remote_path}
mkdir ${queue}
cd ${queue}
put ${filename} ${sha512}
exit
__END_SFTP_CMDS__

      close $remote_sftp;
      if ($? != 0){
         $alive{$remote_host} = 0;
         goto SELECTION;
      }
   }
}


sub get($$$){
   my $queue       = $_[0];
   my $sha512      = $_[1];
   my $replication = $_[2];
   
   foreach $remote_host (crypts($queue, $replication)){
      open my $remote_sftp, "| $SFTP -b- ${remote_host}";
      print $remote_sftp "cd ${remote_path}/${queue}\nget ${sha512}\nexit\n";
      close $remote_sftp;
      if ($? != 0){
        next;
      }else{
        last;
      }
   }
}
