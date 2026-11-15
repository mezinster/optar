/* (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026 */
#include <stdio.h>

#include "optar.h"

int main(void)
{
	unsigned seq;
	int x, y;

	while (scanf("%u", &seq) == 1) {
		seq2xy(&x, &y, seq);
		printf("%u %d %d\n", seq, x, y);
	}
	return 0;
}
