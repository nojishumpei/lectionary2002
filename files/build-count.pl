#!/usr/bin/env perl
# Read-only preflight for this collection's default LuaLaTeX workflow.
# Read latexmk's saved checksums, rather than treating every FORCE target as
# a compilation. Latexmk remains responsible for the actual build decisions.
use strict;
use warnings;
use Cwd qw(abs_path);
use Digest::MD5 ();
use File::Basename qw(dirname);
use File::Spec;

my $force = @ARGV && $ARGV[0] eq '--force' ? shift(@ARGV) : '';
my %states;

sub file_state {
    my ($name, $directory) = @_;
    my $path = File::Spec->rel2abs($name, $directory);
    my $key = abs_path($path) // $path;
    return @{$states{$key}} if exists $states{$key};
    my @stat = stat($path);
    return @{$states{$key} = [-1, '']} unless @stat;
    open my $file, '<:raw', $path or return @{$states{$key} = [-2, '']};
    my $digest = eval { Digest::MD5->new->addfile($file)->hexdigest };
    close $file;
    return @{$states{$key} = [-2, '']} unless defined $digest;
    return @{$states{$key} = [$stat[7], $digest]};
}

sub classify {
    my ($pdf) = @_;
    return 'rebuild' if $force;
    (my $base = $pdf) =~ s/\.pdf$//;
    # Latexmk always requires a LaTeX run when the main aux file is absent.
    return 'rebuild' unless -e "$base.aux";
    open my $database, '<', "$base.fdb_latexmk" or return 'unknown';
    my $version = <$database> // '';
    unless ($version =~ /^# Fdb version 4\s*$/) {
        close $database;
        return 'unknown';
    }
    my ($section, $state, $result, $started, $destination) = ('', '', undef, 0, '');
    my (@inputs, %rewritten);
    my $unsupported = 0;
    while (my $line = <$database>) {
        $line =~ s/^\s+|\s+$//g;
        next if $line eq '' || $line =~ /^[#%]/;
        if ($line =~ /^\["([^"]+)"\]\s+(\S+)\s+"[^"]*"\s+"([^"]*)"\s+"[^"]*"\s+\S+\s+(-?\d+)\s*$/) {
            ($section, $state) = ($1, 'source');
            if ($section eq 'lualatex') {
                ($started, $destination, $result) = ($2, $3, $4);
            } else {
                $unsupported = 1;
            }
            next;
        }
        if ($line =~ /^\[/) { $unsupported = 1; next; }
        next unless $section eq 'lualatex';
        if ($line eq '(source)') { $state = 'source'; next; }
        if ($line eq '(generated)') { $state = 'generated'; next; }
        if ($line eq '(rewritten before read)') { $state = 'rewritten'; next; }
        if ($state eq 'source' && $line =~ /^"([^"]*)"\s+\S+\s+(-?\d+)\s+(\S+)\s+"[^"]*"$/) {
            push @inputs, [$1, $2, $3];
        } elsif ($state eq 'rewritten' && $line =~ /^"([^"]*)"$/) {
            $rewritten{$1} = 1;
        } elsif ($state ne 'generated') {
            $unsupported = 1;
        }
    }
    close $database;
    return 'unknown' if $unsupported || !defined($result) || !@inputs;
    my $directory = dirname(File::Spec->rel2abs($pdf));
    my $saved_pdf = File::Spec->rel2abs($destination, $directory);
    return 'unknown' unless File::Spec->canonpath($saved_pdf) eq
                            File::Spec->canonpath(File::Spec->rel2abs($pdf));
    my $changed = 0;
    for my $input (@inputs) {
        my ($name, $old_size, $old_digest) = @$input;
        next if $rewritten{$name};
        my ($size, $digest) = file_state($name, $directory);
        return 'unknown' if $size == -2;
        next if $size < 0 && $old_size < 0;
        $changed = 1 if $size != $old_size || $digest ne $old_digest;
    }
    return 'rebuild' if $changed || !$started || $result == -1;
    # A prior error can prevent a rerun until an input is corrected. Let
    # latexmk diagnose it instead of claiming it will compile successfully.
    return 'unknown' if $result != 0;
    return -e $pdf ? 'current' : 'rebuild';
}

my %counts = (rebuild => 0, current => 0, unknown => 0);
$counts{classify($_)}++ for @ARGV;
my $total = scalar @ARGV;
printf "PDF rebuild estimate: %d of %d (%d up to date", $counts{rebuild}, $total, $counts{current};
printf "; %d awaiting latexmk's check", $counts{unknown} if $counts{unknown};
print ").\n";
